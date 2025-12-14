"""
tools.py - Custom Tools using ADK's ToolContext for state management
=====================================================================

Key Concepts:
- ToolContext: ADK automatically injects this when you add `tool_context` parameter
- tool_context.state: A dictionary to read/write session state
- output_key: Automatically saves agent's response to state (set in planner.py)


"""

from google.adk.tools import ToolContext

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


def calculate_profit(tool_context: ToolContext, labor_cost: float = 50.0) -> dict:
    # Pull the actual agent outputs from state (output_key results)
    fabric_cost_raw = tool_context.state.get("fabric_cost", {})
    market_price_raw = tool_context.state.get("market_price", {})

    fabric_cost = _coerce_json_dict(fabric_cost_raw)
    market_price = _coerce_json_dict(market_price_raw)

    # --- Fabric math (Agent B output) ---
    price_per_yard = float(fabric_cost.get("price_per_yard", 0) or 0)
    yards_needed = float(fabric_cost.get("yards_needed", 0) or 0)
    fabric_total_cost = round(price_per_yard * yards_needed, 2)

    # --- Revenue math (Agent C output) ---
    selling_price = float(market_price.get("average_price", 0) or 0)

    # --- Profitability ---
    total_cost = fabric_total_cost + labor_cost
    profit = selling_price - total_cost
    margin = (profit / selling_price) if selling_price > 0 else 0.0

    result = {
        "fabric_cost": fabric_total_cost,
        "labor_cost": labor_cost,
        "total_cost": round(total_cost, 2),
        "selling_price": selling_price,
        "profit": round(profit, 2),
        "profit_margin_percent": round(margin * 100, 1),
        "target_margin_percent": TARGET_PROFIT_MARGIN * 100,
        "is_profitable": margin >= TARGET_PROFIT_MARGIN,
    }

    # Save to state for the optimizer / debugging
    tool_context.state["profit_analysis"] = result
    return result



# ============================================================================