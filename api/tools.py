"""Tool (function-calling) schemas exposed to Gemma, in Ollama's tool format.

Each schema's `name` maps 1:1 to a function in queries.py — see
assistant.py::TOOL_DISPATCH for the actual wiring.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_foods",
            "description": (
                "Search the Nigerian food database for dishes matching filters. "
                "Returns each match's macros, estimated cost in Naira, dietary tags, "
                "allergens, and how much of its ingredient list the user's pantry already "
                "covers (pantry_coverage). Use this before recommending any specific dish."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cook_time_category": {
                        "type": "string",
                        "enum": ["fast", "intermediate", "long"],
                        "description": "fast=5-10 min, intermediate=30-60 min, long=60-120 min",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                    },
                    "preference": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Dietary tags the dish must ALL have, e.g. ['High Protein','Halal']",
                    },
                    "allergy": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Allergens the dish must have NONE of, e.g. ['Peanuts']",
                    },
                    "pantry": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ingredient names the user already has on hand",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe",
            "description": "Get the full recipe (ingredients with quantities, and ordered steps) for one food, by its id from get_foods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "food_id": {"type": "integer"},
                },
                "required": ["food_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shoplist_price",
            "description": "Estimate the Naira cost of whatever ingredients aren't already in the pantry, for a given set of planned foods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "food_ids": {"type": "array", "items": {"type": "integer"}},
                    "pantry": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["food_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Sum calories, macros and estimated cost across a set of foods (e.g. a day's or week's planned meals).",
            "parameters": {
                "type": "object",
                "properties": {
                    "food_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["food_ids"],
            },
        },
    },
]
