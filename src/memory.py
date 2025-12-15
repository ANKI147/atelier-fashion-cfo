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

def save_optimization_flag(
    needs_optimization: str,
    tool_context: ToolContext
) -> str:
    """
    Saves optimization flag to session state.
    
    Args:
        needs_optimization: Boolean indicating if optimization is needed.
    
    Returns:
        Confirmation message
    """
    tool_context.state["needs_optimization"] = needs_optimization

    if needs_optimization.lower() == "initial":
        status = "not yet determined"
    elif needs_optimization.lower() == "needed":    
        status = "needed"
    elif needs_optimization.lower() == "not needed":
        status = "not needed"    
    return f"✅ Optimization flag saved: Optimization is {status}."