"""The tool-calling loop: user message -> Gemma -> (tool calls -> queries.py)* -> reply.

This is the piece that actually lets Gemma use get_foods/get_recipe/
calculator/get_shoplist_price instead of guessing food data from training
knowledge.
"""

import json
from typing import Optional

import db
import queries
from config import resolve
from ollama_client import chat as ollama_chat
from tools import TOOLS

TOOL_DISPATCH = {
    "get_foods": lambda conn, args: queries.get_foods(
        conn,
        cook_time_category=args.get("cook_time_category"),
        meal_type=args.get("meal_type"),
        preferences=args.get("preference"),
        allergies=args.get("allergy"),
        pantry=args.get("pantry"),
    ),
    "get_recipe": lambda conn, args: queries.get_recipe(
        conn, args["food_id"], pantry=args.get("pantry")
    ),
    "get_shoplist_price": lambda conn, args: queries.get_shoplist_price(
        conn, args["food_ids"], pantry=args.get("pantry")
    ),
    "calculator": lambda conn, args: queries.calculate_totals(conn, args["food_ids"]),
}

SYSTEM_PROMPT = (
    "You are NutriMate, an on-device nutrition coach for Nigerian university students "
    "on tight budgets. You have tools to search real Nigerian dishes, pull recipes, "
    "price a shopping list, and total up nutrition/cost — always call a tool instead of "
    "guessing food data; never invent a dish, price, or nutrition number yourself. "
    "Keep replies short, concrete, and budget-aware. Prices are in Naira (₦)."
)

MAX_TOOL_ROUNDS = 4


def _parse_arguments(raw) -> dict:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw or {}


def run_chat(
    user_message: str,
    history: list[dict],
    provider: Optional[str] = None,
    user_context: Optional[dict] = None,
) -> dict:
    """Returns {reply, provider, model, tool_calls}. Raises OllamaError on failure
    (config.resolve raises ValueError for a bad provider name; ollama_client raises
    OllamaError for connectivity/auth/model problems) — let the API layer translate
    those into HTTP responses.
    """
    cfg = resolve(provider)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_context:
        messages.append({"role": "system", "content": f"Known user context: {json.dumps(user_context)}"})
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    conn = db.get_connection()
    tool_trace = []
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            result = ollama_chat(cfg, messages, tools=TOOLS)
            message = result.get("message", {})
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return {
                    "reply": (message.get("content") or "").strip(),
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "tool_calls": tool_trace,
                }

            messages.append(message)
            for call in tool_calls:
                fn_name = call["function"]["name"]
                args = _parse_arguments(call["function"].get("arguments"))
                handler = TOOL_DISPATCH.get(fn_name)

                if handler is None:
                    tool_result = {"error": f"Unknown tool '{fn_name}'"}
                else:
                    try:
                        tool_result = handler(conn, args)
                    except Exception as e:  # keep the loop alive; let Gemma see the error and recover
                        tool_result = {"error": str(e)}

                tool_trace.append({"name": fn_name, "arguments": args})
                messages.append({"role": "tool", "name": fn_name, "content": json.dumps(tool_result)})

        return {
            "reply": "I looked into a few things but didn't land on an answer — could you rephrase that?",
            "provider": cfg.provider,
            "model": cfg.model,
            "tool_calls": tool_trace,
        }
    finally:
        conn.close()
