"""Pydantic response models for the API."""

from typing import Any, Literal, Optional
from pydantic import BaseModel


class PantryCoverage(BaseModel):
    matched: int
    required: int
    ratio: float  # matched / required, 1.0 if the food needs no ingredients at all


class FoodSummary(BaseModel):
    id: int
    name: str
    meal_type: str
    cook_time_category: str
    prep_time_minutes: int
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float]
    estimated_cost_naira: int
    serves: int
    region: Optional[str]
    dietary_tags: list[str]
    allergens: list[str]
    pantry_coverage: PantryCoverage


class IngredientLine(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    is_optional: bool
    avg_price_naira: float


class RecipeStep(BaseModel):
    step_number: int
    instruction: str


class FoodRecipe(BaseModel):
    food: FoodSummary
    instructions_summary: Optional[str]
    ingredients: list[IngredientLine]
    steps: list[RecipeStep]


class ShopListItem(BaseModel):
    ingredient: str
    category: str
    quantity_needed: float
    unit: str
    unit_price_naira: float
    estimated_price_naira: float
    needed_for: list[str]  # food names that require this ingredient


class ShopListResult(BaseModel):
    items: list[ShopListItem]
    total_estimated_price_naira: float


class CalculatorRequest(BaseModel):
    food_ids: list[int]


class CalculatorResult(BaseModel):
    food_count: int
    total_calories: int
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    total_cost_naira: int


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    provider: Optional[Literal["local", "cloud"]] = None  # None = server default
    # Optional known-user context (budget, pantry, preferences, allergies) so
    # Gemma doesn't have to re-ask things the app already knows.
    context: Optional[dict[str, Any]] = None


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict[str, Any]


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    tool_calls: list[ToolCallTrace]


class ModelConfig(BaseModel):
    provider: str
    model: str


class ConfigResponse(BaseModel):
    default_provider: str
    local: ModelConfig
    cloud: ModelConfig
    cloud_configured: bool
