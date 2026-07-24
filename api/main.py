"""NutriMate AI backend — exposes the four Gemma tool functions over HTTP.

Run from Backend/api:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import assistant
import config
import db
import queries
from ollama_client import OllamaError
from schemas import (
    CalculatorRequest,
    CalculatorResult,
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    FoodRecipe,
    FoodSummary,
    ShopListResult,
)

app = FastAPI(title="NutriMate AI API", version="0.1.0")

# The Vite dev server (see Frontend/) and its default preview port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/foods", response_model=list[FoodSummary])
def list_foods(
    cook_time_category: Optional[str] = Query(None, description="fast | intermediate | long"),
    meal_type: Optional[str] = Query(None, description="breakfast | lunch | dinner | snack"),
    preference: Optional[list[str]] = Query(None, description="Dietary tags the food must all have"),
    allergy: Optional[list[str]] = Query(None, description="Allergens the food must NOT have"),
    pantry: Optional[list[str]] = Query(None, description="Ingredient names the user already has"),
):
    conn = db.get_connection()
    try:
        return queries.get_foods(
            conn,
            cook_time_category=cook_time_category,
            meal_type=meal_type,
            preferences=preference,
            allergies=allergy,
            pantry=pantry,
        )
    finally:
        conn.close()


@app.get("/foods/{food_id}/recipe", response_model=FoodRecipe)
def food_recipe(food_id: int, pantry: Optional[list[str]] = Query(None)):
    conn = db.get_connection()
    try:
        result = queries.get_recipe(conn, food_id, pantry=pantry)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No food with id {food_id}")
        return result
    finally:
        conn.close()


@app.get("/shoplist-price", response_model=ShopListResult)
def shoplist_price(
    food_ids: list[int] = Query(..., description="Foods planned for the week"),
    pantry: Optional[list[str]] = Query(None, description="Ingredients already on hand"),
):
    conn = db.get_connection()
    try:
        return queries.get_shoplist_price(conn, food_ids, pantry=pantry)
    finally:
        conn.close()


@app.post("/calculator", response_model=CalculatorResult)
def calculator(payload: CalculatorRequest):
    conn = db.get_connection()
    try:
        return queries.calculate_totals(conn, payload.food_ids)
    finally:
        conn.close()


@app.get("/config", response_model=ConfigResponse)
def get_config():
    """Lets the frontend show which model is active and whether cloud is usable."""
    return {
        "default_provider": config.DEFAULT_PROVIDER,
        "local": {"provider": "local", "model": config.LOCAL_MODEL},
        "cloud": {"provider": "cloud", "model": config.CLOUD_MODEL},
        "cloud_configured": config.cloud_is_configured(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        result = assistant.run_chat(
            user_message=payload.message,
            history=[m.model_dump() for m in payload.history],
            provider=payload.provider,
            user_context=payload.context,
        )
    except ValueError as e:  # bad provider name
        raise HTTPException(status_code=400, detail=str(e))
    except OllamaError as e:  # unreachable daemon, missing cloud key, model not pulled, etc.
        raise HTTPException(status_code=502, detail=str(e))
    return result
