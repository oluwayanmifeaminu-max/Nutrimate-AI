"""The four Gemma tool functions, implemented as plain SQL over nutrimate.db.

Kept deliberately un-clever: this dataset is tens of dishes, not millions of
rows, so N+1-ish per-food lookups read more clearly than one giant join and
cost nothing in practice.

Known simplification (documented, not hidden): ingredient quantities are
priced using the ingredient's own `avg_price_naira` (price per one
`default_unit`), regardless of what unit a given recipe happens to specify.
There's no unit-conversion layer yet (e.g. tsp -> kg). Good enough for an
MVP estimate; worth revisiting once real pricing data is in.
"""

import sqlite3
from typing import Optional


def _normalize_pantry(pantry: Optional[list[str]]) -> set[str]:
    return {p.strip().lower() for p in (pantry or []) if p.strip()}


def _food_tags(conn: sqlite3.Connection, food_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT dt.name FROM food_dietary_tags fdt
        JOIN dietary_tags dt ON dt.id = fdt.tag_id
        WHERE fdt.food_id = ?
        ORDER BY dt.name
        """,
        (food_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _food_allergens(conn: sqlite3.Connection, food_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT a.name FROM food_allergens fa
        JOIN allergens a ON a.id = fa.allergen_id
        WHERE fa.food_id = ?
        ORDER BY a.name
        """,
        (food_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _food_ingredients(conn: sqlite3.Connection, food_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT i.name, i.category, i.default_unit, i.avg_price_naira,
               fi.quantity, fi.unit, fi.is_optional
        FROM food_ingredients fi
        JOIN ingredients i ON i.id = fi.ingredient_id
        WHERE fi.food_id = ?
        ORDER BY fi.is_optional, i.name
        """,
        (food_id,),
    ).fetchall()


def _pantry_coverage(ingredient_rows: list[sqlite3.Row], pantry: set[str]) -> dict:
    required = [r for r in ingredient_rows if not r["is_optional"]]
    if not required:
        return {"matched": 0, "required": 0, "ratio": 1.0}
    matched = sum(1 for r in required if r["name"].strip().lower() in pantry)
    return {"matched": matched, "required": len(required), "ratio": matched / len(required)}


def _food_summary(conn: sqlite3.Connection, row: sqlite3.Row, pantry: set[str]) -> dict:
    ingredient_rows = _food_ingredients(conn, row["id"])
    return {
        "id": row["id"],
        "name": row["name"],
        "meal_type": row["meal_type"],
        "cook_time_category": row["cook_time_category_id"],
        "prep_time_minutes": row["prep_time_minutes"],
        "calories": row["calories"],
        "protein_g": row["protein_g"],
        "carbs_g": row["carbs_g"],
        "fat_g": row["fat_g"],
        "fiber_g": row["fiber_g"],
        "estimated_cost_naira": row["estimated_cost_naira"],
        "serves": row["serves"],
        "region": row["region"],
        "dietary_tags": _food_tags(conn, row["id"]),
        "allergens": _food_allergens(conn, row["id"]),
        "pantry_coverage": _pantry_coverage(ingredient_rows, pantry),
    }


def get_foods(
    conn: sqlite3.Connection,
    cook_time_category: Optional[str] = None,
    meal_type: Optional[str] = None,
    preferences: Optional[list[str]] = None,
    allergies: Optional[list[str]] = None,
    pantry: Optional[list[str]] = None,
) -> list[dict]:
    """get_foods(cook_time_category, pantry, preference, allergy).

    - `preferences` (dietary tags) are ANDed: a food must carry every tag given.
    - `allergies` are excluded: a food is dropped if it carries ANY of them.
    - `pantry` does not filter results — it only scores how much of each
      food's required ingredient list the caller already has, via
      `pantry_coverage`. Results are sorted by that coverage, best first, so
      "what can I make with what I already have" naturally floats to the top.
    """
    clauses = []
    params: list = []

    if cook_time_category:
        clauses.append("f.cook_time_category_id = ?")
        params.append(cook_time_category)

    if meal_type:
        clauses.append("f.meal_type = ?")
        params.append(meal_type)

    if allergies:
        placeholders = ",".join("?" for _ in allergies)
        clauses.append(
            f"""f.id NOT IN (
                SELECT fa.food_id FROM food_allergens fa
                JOIN allergens a ON a.id = fa.allergen_id
                WHERE a.name IN ({placeholders})
            )"""
        )
        params.extend(allergies)

    if preferences:
        placeholders = ",".join("?" for _ in preferences)
        clauses.append(
            f"""f.id IN (
                SELECT fdt.food_id FROM food_dietary_tags fdt
                JOIN dietary_tags dt ON dt.id = fdt.tag_id
                WHERE dt.name IN ({placeholders})
                GROUP BY fdt.food_id
                HAVING COUNT(DISTINCT dt.name) = ?
            )"""
        )
        params.extend(preferences)
        params.append(len(preferences))

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(f"SELECT * FROM foods f {where_sql} ORDER BY f.name", params).fetchall()

    pantry_set = _normalize_pantry(pantry)
    foods = [_food_summary(conn, row, pantry_set) for row in rows]
    foods.sort(key=lambda f: f["pantry_coverage"]["ratio"], reverse=True)
    return foods


def get_recipe(conn: sqlite3.Connection, food_id: int, pantry: Optional[list[str]] = None) -> Optional[dict]:
    """get_recipe(food)."""
    row = conn.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    if row is None:
        return None

    pantry_set = _normalize_pantry(pantry)
    ingredient_rows = _food_ingredients(conn, food_id)
    steps = conn.execute(
        "SELECT step_number, instruction FROM recipe_steps WHERE food_id = ? ORDER BY step_number",
        (food_id,),
    ).fetchall()

    return {
        "food": _food_summary(conn, row, pantry_set),
        "instructions_summary": row["instructions_summary"],
        "ingredients": [
            {
                "name": r["name"],
                "category": r["category"],
                "quantity": r["quantity"],
                "unit": r["unit"],
                "is_optional": bool(r["is_optional"]),
                "avg_price_naira": r["avg_price_naira"],
            }
            for r in ingredient_rows
        ],
        "steps": [{"step_number": s["step_number"], "instruction": s["instruction"]} for s in steps],
    }


def get_shoplist_price(conn: sqlite3.Connection, food_ids: list[int], pantry: Optional[list[str]] = None) -> dict:
    """get_shoplist_price() — estimate the cost of whatever isn't already in the pantry."""
    pantry_set = _normalize_pantry(pantry)

    # ingredient name -> accumulated line data
    lines: dict[tuple[str, str], dict] = {}

    for food_id in food_ids:
        food_row = conn.execute("SELECT name FROM foods WHERE id = ?", (food_id,)).fetchone()
        if food_row is None:
            continue
        food_name = food_row["name"]

        for r in _food_ingredients(conn, food_id):
            if r["is_optional"]:
                continue
            if r["name"].strip().lower() in pantry_set:
                continue

            key = (r["name"], r["unit"])
            if key not in lines:
                lines[key] = {
                    "ingredient": r["name"],
                    "category": r["category"],
                    "quantity_needed": 0.0,
                    "unit": r["unit"],
                    "unit_price_naira": r["avg_price_naira"],
                    "needed_for": [],
                }
            lines[key]["quantity_needed"] += r["quantity"]
            lines[key]["needed_for"].append(food_name)

    items = []
    total = 0.0
    for line in lines.values():
        estimated = round(line["quantity_needed"] * line["unit_price_naira"], 2)
        total += estimated
        items.append({**line, "estimated_price_naira": estimated})

    items.sort(key=lambda x: x["ingredient"])
    return {"items": items, "total_estimated_price_naira": round(total, 2)}


def calculate_totals(conn: sqlite3.Connection, food_ids: list[int]) -> dict:
    """calculator() — pure aggregation over the selected foods' recorded macros/cost."""
    if not food_ids:
        return {
            "food_count": 0, "total_calories": 0, "total_protein_g": 0.0,
            "total_carbs_g": 0.0, "total_fat_g": 0.0, "total_fiber_g": 0.0, "total_cost_naira": 0,
        }

    placeholders = ",".join("?" for _ in food_ids)
    rows = conn.execute(
        f"SELECT calories, protein_g, carbs_g, fat_g, fiber_g, estimated_cost_naira FROM foods WHERE id IN ({placeholders})",
        food_ids,
    ).fetchall()

    return {
        "food_count": len(rows),
        "total_calories": sum(r["calories"] for r in rows),
        "total_protein_g": round(sum(r["protein_g"] for r in rows), 1),
        "total_carbs_g": round(sum(r["carbs_g"] for r in rows), 1),
        "total_fat_g": round(sum(r["fat_g"] for r in rows), 1),
        "total_fiber_g": round(sum(r["fiber_g"] or 0 for r in rows), 1),
        "total_cost_naira": sum(r["estimated_cost_naira"] for r in rows),
    }
