"""
tools.py - Custom Tools using ADK's ToolContext for state management
=====================================================================

Key Concepts:
- ToolContext: ADK automatically injects this when you add `tool_context` parameter
- tool_context.state: A dictionary to read/write session state
- output_key: Automatically saves agent's response to state (set in planner.py)


"""

from google.adk.tools import ToolContext
# tools.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Configuration
TARGET_PROFIT_MARGIN = 0.40



# ============================================================================
# TOOL 4: Find Cheaper Alternative (Agent B - during optimization)
# ============================================================================
def find_cheaper_alternative(
    current_fabric: str,
    tool_context: ToolContext
) -> dict:
    """
    Suggests a cheaper fabric alternative.
    
    Args:
        current_fabric: The expensive fabric to replace
    
    Returns:
        Dictionary with alternative suggestion
    """
    # Simple lookup - in production, this could also use Google Search
    alternatives = {
        "Silk Charmeuse": {"name": "Polyester Satin", "estimated_price": 4.00},
        "Silk": {"name": "Rayon", "estimated_price": 5.00},
        "Wool Gabardine": {"name": "Polyester Blend", "estimated_price": 6.00},
        "Velvet": {"name": "Velour", "estimated_price": 8.00},
        "Cotton Sateen": {"name": "Poly-Cotton Blend", "estimated_price": 3.50},
    }
    
    alt = alternatives.get(current_fabric, {"name": "Synthetic Blend", "estimated_price": 4.00})
    
    # Store the suggestion in state
    tool_context.state["suggested_alternative"] = alt["name"]
    
    return {
        "original_fabric": current_fabric,
        "alternative_fabric": alt["name"],
        "estimated_price_per_yard": alt["estimated_price"],
        "action": f"Search Google for: wholesale price {alt['name']} fabric per yard"
    }


# ============================================================================
# TOOL 5: Calculate Profit (Agent D)
# ============================================================================

import json
from typing import Optional
from google.adk.tools import ToolContext

# keep your existing TARGET_PROFIT_MARGIN and _coerce_json_dict(value) here

def _coerce_json_dict(value):
    """
    Your agents currently store fabric_cost / market_price like:
      "{\"fabric_name\": \"Wool Suiting\", ... }"
    i.e., a JSON-encoded dict stored as a Python string.

    This helper accepts either:
    - dict (already parsed)
    - JSON string (your current output)
    and returns a dict or {}.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}




def _estimate_labor_cost_from_specs(specs: dict, hourly_rate: float = 10.0) -> float:
    """
    Simple heuristic (tune as you like):
    - Base hours depend on garment_type
    - Complexity adjusts via multiplier
    - Yardage beyond 3.0 adds handling time
    """
    garment_type = (specs.get("garment_type") or "").lower()
    complexity = (specs.get("construction_complexity") or "Medium").lower()
    yards = float(specs.get("estimated_yardage", 0) or 0)

    base_hours_by_type = {
        "dress": 6.0,
        "outerwear": 8.0,
        "top": 3.5,
        "bottom": 4.0,
    }
    base_hours = base_hours_by_type.get(garment_type, 5.0)

    mult = {"low": 0.85, "medium": 1.0, "high": 1.35}.get(complexity, 1.0)

    extra_hours = max(0.0, yards - 3.0) * 0.5

    hours = (base_hours + extra_hours) * mult
    return round(hours * hourly_rate, 2)


def _choose_selling_price(market_price: dict) -> float:
    """
    Your rule:
    - High Demand: (average_price + price_range_high) / 2
    - Low Demand:  (average_price + price_range_low) / 2
    - Medium Demand: average_price
    """
    avg = float(market_price.get("average_price", 0) or 0)
    low = float(market_price.get("price_range_low", 0) or 0)
    high = float(market_price.get("price_range_high", 0) or 0)
    trend = (market_price.get("trend_status") or "").strip().lower()

    # Fallbacks if low/high missing
    if low <= 0:
        low = avg
    if high <= 0:
        high = avg

    if "high" in trend:
        return round((avg + high) / 2.0, 2)
    if "low" in trend:
        return round((avg + low) / 2.0, 2)
    return round(avg, 2)


def calculate_profit(tool_context: ToolContext, labor_cost: Optional[float] = None) -> dict:
    # Pull the actual agent outputs from state (output_key results)
    fabric_cost_raw = tool_context.state.get("fabric_cost", {})
    market_price_raw = tool_context.state.get("market_price", {})
    garment_specs = tool_context.state.get("garment_specs", {}) or {}

    fabric_cost = _coerce_json_dict(fabric_cost_raw)
    market_price = _coerce_json_dict(market_price_raw)

    # --- Fabric math (Agent B output) ---
    price_per_yard = float(fabric_cost.get("price_per_yard", 0) or 0)
    yards_needed = float(fabric_cost.get("yards_needed", 0) or 0)
    fabric_total_cost = round(price_per_yard * yards_needed, 2)

    # --- Revenue math (Agent C output) ---
    selling_price = _choose_selling_price(market_price)

    # --- Labor math (NEW; uses garment specs) ---
    if labor_cost is None:
        labor_cost = _estimate_labor_cost_from_specs(garment_specs, hourly_rate=10.0)

    # --- Profitability ---
    total_cost = round(fabric_total_cost + float(labor_cost), 2)
    profit = round(selling_price - total_cost, 2)
    margin = (profit / selling_price) if selling_price > 0 else 0.0

    result = {
        "fabric_cost": fabric_total_cost,
        "labor_cost": float(labor_cost),
        "total_cost": total_cost,
        "selling_price": selling_price,
        "profit": profit,
        "profit_margin_percent": round(margin * 100, 1),
        "target_margin_percent": TARGET_PROFIT_MARGIN * 100,
        "is_profitable": margin >= TARGET_PROFIT_MARGIN,

        # Optional debug fields (safe to remove):
        "trend_status": market_price.get("trend_status"),
    }

    tool_context.state["profit_analysis"] = result
    return result


def serpapi_google_shopping_market_price(
    garment_query: str,
    tool_context: ToolContext,
    gl: str = "us",
    hl: str = "en",
    location: str = "United States",
    max_results: int = 20,
) -> dict:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY missing in environment")

    params = {
        "engine": "google_shopping",
        "q": garment_query,
        "gl": gl,
        "hl": hl,
        "location": location,
        "api_key": api_key,
    }

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # SerpApi returns shopping listings in `shopping_results`
    items = data.get("shopping_results", [])[:max_results]

    prices = []
    sources = []
    for it in items:
        p = it.get("extracted_price")
        if isinstance(p, (int, float)) and p > 0:
            prices.append(float(p))
        src = it.get("source")
        if isinstance(src, str) and src:
            sources.append(src)

    if not prices:
        result = {
            "garment_name": garment_query,
            "average_price": 0.0,
            "price_range_low": 0.0,
            "price_range_high": 0.0,
            "trend_status": "Low Demand",

        }
        tool_context.state["market_price"] = result
        return result

    low = min(prices)
    high = max(prices)
    avg = round(sum(prices) / len(prices), 2)

    # Simple heuristic; refine later if you want
    trend = "High Demand" if len(prices) >= 15 else ("Medium Demand" if len(prices) >= 6 else "Low Demand")

    result = {
        "garment_name": garment_query,
        "average_price": avg,
        "price_range_low": round(low, 2),
        "price_range_high": round(high, 2),
        "trend_status": trend,
    

    }

    # This is what your optimizer reads via calculate_profit()
    tool_context.state["market_price"] = result
    return result

# ============================================================================