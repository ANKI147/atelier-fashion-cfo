from google.adk.tools import ToolContext

# ============================================================================
# TOOL 1: Save Garment Specs (Agent A)
# ============================================================================
def save_garment_specs(
    garment_type: str,
    garment_name: str,
    silhoutte: str,
    length: str,
    sleeves: str,
    neckline: str,
    fabric_confidence: float,   
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
        "silhoutte": silhoutte,
        "length": length,
        "sleeves": sleeves ,
        "neckline": neckline,
        "fabric_confidence": fabric_confidence,   
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

