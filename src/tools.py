"""
tools.py - Custom Tools using ADK's ToolContext for state management
=====================================================================

Key Concepts:
- ToolContext: ADK automatically injects this when you add `tool_context` parameter
- tool_context.state: A dictionary to read/write session state
- output_key: Automatically saves agent's response to state (set in planner.py)

NO external memory module needed - ADK handles it!
"""

from google.adk.tools import ToolContext

# Configuration
TARGET_PROFIT_MARGIN = 0.40


# ============================================================================
# TOOL 1: Save Garment Specs (Agent A)
# ============================================================================
def save_garment_specs(
    garment_type: str,
    garment_name: str,
    primary_fabric: str,
    estimated_yardage: float,
    construction_complexity: str,
    tool_context: ToolContext  # ADK injects this automatically!
) -> str:
    """
    Saves the garment analysis to session state.
    
    Args:
        garment_type: Type of garment (dress, top, pants, etc.)
        garment_name: Specific name (e.g., "Bias-Cut Slip Dress")
        primary_fabric: The identified fabric type
        estimated_yardage: Yards of fabric needed
        construction_complexity: Low, Medium, or High
    
    Returns:
        Confirmation message
    """
    # Save to session state - other agents can read this!
    tool_context.state["garment_specs"] = {
        "garment_type": garment_type,
        "garment_name": garment_name,
        "primary_fabric": primary_fabric,
        "estimated_yardage": estimated_yardage,
        "construction_complexity": construction_complexity
    }
    
    return f"✅ Specs saved: {garment_name} made of {primary_fabric}, {estimated_yardage} yards needed."


# ============================================================================
# TOOL 2: Save Fabric Cost (Agent B) 
# ============================================================================
def save_fabric_cost(
    fabric_name: str,
    price_per_yard: float,
    yards_needed: float,
    source: str,
    tool_context: ToolContext
) -> str:
    """
    Saves fabric pricing to session state after Google Search.
    
    Args:
        fabric_name: Name of the fabric
        price_per_yard: Cost per yard found from search
        yards_needed: How many yards required
        source: Where the price was found
    
    Returns:
        Confirmation with total cost
    """
    total_cost = price_per_yard * yards_needed
    
    tool_context.state["fabric_pricing"] = {
        "fabric_name": fabric_name,
        "price_per_yard": price_per_yard,
        "yards_needed": yards_needed,
        "total_cost": round(total_cost, 2),
        "source": source
    }
    
    return f"✅ Fabric cost saved: {fabric_name} at ${price_per_yard}/yard = ${total_cost:.2f} total"


# ============================================================================
# TOOL 3: Save Market Price (Agent C)
# ============================================================================
def save_market_price(
    garment_name: str,
    average_price: float,
    price_range_low: float,
    price_range_high: float,
    trend_status: str,
    tool_context: ToolContext
) -> str:
    """
    Saves market research to session state after Google Search.
    
    Args:
        garment_name: Name of the garment researched
        average_price: Average selling price found
        price_range_low: Lowest price found
        price_range_high: Highest price found
        trend_status: Current trend (High Demand, Low Demand, etc.)
    
    Returns:
        Confirmation message
    """
    tool_context.state["market_data"] = {
        "garment_name": garment_name,
        "average_price": average_price,
        "price_range": {"low": price_range_low, "high": price_range_high},
        "trend_status": trend_status
    }
    
    return f"✅ Market data saved: {garment_name} sells for ${average_price:.2f} avg ({trend_status})"


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
def calculate_profit(
    tool_context: ToolContext,
    labor_cost: float = 50.0
) -> dict:
    """
    Calculates profit using data from session state.
    Reads fabric_pricing and market_data saved by other agents.
    
    Args:
        labor_cost: Cost of labor (default $50)
    
    Returns:
        Profit analysis dictionary
    """
    # Read from session state (saved by Agents B and C)
    fabric_data = tool_context.state.get("fabric_pricing", {})
    market_data = tool_context.state.get("market_data", {})
    
    fabric_cost = fabric_data.get("total_cost", 0)
    selling_price = market_data.get("average_price", 0)
    
    # Calculate
    total_cost = fabric_cost + labor_cost
    profit = selling_price - total_cost
    margin = profit / selling_price if selling_price > 0 else 0
    
    result = {
        "fabric_cost": fabric_cost,
        "labor_cost": labor_cost,
        "total_cost": round(total_cost, 2),
        "selling_price": selling_price,
        "profit": round(profit, 2),
        "profit_margin_percent": round(margin * 100, 1),
        "target_margin_percent": TARGET_PROFIT_MARGIN * 100,
        "is_profitable": margin >= TARGET_PROFIT_MARGIN
    }
    
    # Save to state for reference
    tool_context.state["profit_analysis"] = result
    
    return result