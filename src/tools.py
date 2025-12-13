TARGET_PROFIT_MARGIN = 0.40

def analyze_garment(description: str) -> dict:
    """
    Looks at the garment and figures out what it's made of.
    
    In a real app, this would use Gemini Vision to analyze an image.
    For now, we return mock data to demonstrate the concept.
    
    Args:
        description: What the user said about their design
        
    Returns:
        Dictionary with garment details
    """
    # Mock response - in production, call Gemini Vision API
    return {
        "garment_type": "Maxi Dress",
        "fabric": "Silk Charmeuse",
        "yards_needed": 4.5,
        "complexity": "High",
        "color": "Emerald Green"
    }


# ============================================================================
# TOOL 2: Get Fabric Price (Used by Agent B)
# ============================================================================
def get_fabric_price(fabric_name: str, yards: float) -> dict:
    """
    Finds how much the fabric costs from wholesalers.
    
    Args:
        fabric_name: Type of fabric (e.g., "Silk Charmeuse")
        yards: How many yards we need
        
    Returns:
        Dictionary with pricing info
    """
    # Price database (mock data)
    prices = {
        "Silk Charmeuse": 10.00,
        "Polyester Satin": 3.50,
        "Cotton": 5.00,
        "Velvet": 15.00
    }
    
    price_per_yard = prices.get(fabric_name, 8.00)
    total = price_per_yard * yards
    
    return {
        "fabric": fabric_name,
        "price_per_yard": price_per_yard,
        "yards": yards,
        "total_cost": round(total, 2)
    }


# ============================================================================
# TOOL 3: Get Market Price (Used by Agent C)
# ============================================================================
def get_market_price(garment_type: str) -> dict:
    """
    Finds what similar items sell for in the market.
    
    Args:
        garment_type: Type of garment (e.g., "Maxi Dress")
        
    Returns:
        Dictionary with market data
    """
    # Market prices (mock data)
    market_prices = {
        "Maxi Dress": 120.00,
        "Mini Dress": 80.00,
        "Blouse": 60.00,
        "Pants": 90.00
    }
    
    return {
        "garment_type": garment_type,
        "average_selling_price": market_prices.get(garment_type, 100.00),
        "trend": "High Demand"
    }


# ============================================================================
# TOOL 4: Find Cheaper Fabric (Used by Agent B during optimization)
# ============================================================================
def find_cheaper_fabric(current_fabric: str) -> dict:
    """
    Finds a cheaper alternative fabric.
    Used during the optimization loop when profit is too low.
    
    Args:
        current_fabric: The expensive fabric we want to replace
        
    Returns:
        Dictionary with alternative fabric info
    """
    alternatives = {
        "Silk Charmeuse": {"name": "Polyester Satin", "price": 3.50},
        "Velvet": {"name": "Velour", "price": 8.00},
    }
    
    alt = alternatives.get(current_fabric, {"name": "Cotton Blend", "price": 4.00})
    
    return {
        "original": current_fabric,
        "alternative": alt["name"],
        "new_price_per_yard": alt["price"]
    }


# ============================================================================
# TOOL 5: Calculate Profit (Used by Agent D)
# ============================================================================
def calculate_profit(fabric_cost: float, selling_price: float, labor_cost: float = 50.0) -> dict:
    """
    Calculates if we're making enough profit.
    
    Args:
        fabric_cost: Total cost of fabric
        selling_price: What we'll sell it for
        labor_cost: Cost to make it (default $50)
        
    Returns:
        Dictionary with profit analysis
    """
    total_cost = fabric_cost + labor_cost
    profit = selling_price - total_cost
    margin = profit / selling_price if selling_price > 0 else 0
    
    return {
        "fabric_cost": fabric_cost,
        "labor_cost": labor_cost,
        "total_cost": total_cost,
        "selling_price": selling_price,
        "profit": round(profit, 2),
        "profit_margin": round(margin * 100, 1),
        "target_margin": TARGET_PROFIT_MARGIN * 100,
        "is_profitable": margin >= TARGET_PROFIT_MARGIN
    }