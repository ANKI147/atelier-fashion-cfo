import os
import time
import json
from duckduckgo_search import DDGS
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import agentql
TARGET_PROFIT_MARGIN = 0.40

# ============================================================================
# CONFIGURATION & LIMITS
# ============================================================================
# Gemini 1.5 Flash: 15 RPM (Requests Per Minute)
# We add a small sleep to ensure we never hit the rate limit error
SAFETY_DELAY = 4.0  

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ============================================================================
# TOOL 1: Analyze Garment (Vision)
# ============================================================================
def analyze_garment(image_path: str) -> dict:
    """
    Uses Gemini 1.5 Flash (Free Tier: 1500/day).
    """
    time.sleep(SAFETY_DELAY) # Prevent hitting 15 RPM limit
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # ... (Image loading logic same as before) ...
        
        # Simplified for brevity - assumes image_data is loaded
        # response = model.generate_content(...) 
        
        # Mock return for successful connection verification
        return {"garment": "Silk Dress", "confidence": "High"}
        
    except Exception as e:
        if "429" in str(e):
            return {"error": "Hit Gemini Rate Limit. Please wait 60s."}
        return {"error": str(e)}

# ============================================================================
# TOOL 2: Sourcing (Smart Fallback System)
# ============================================================================
def get_fabric_price(fabric_name: str) -> dict:
    """
    Attempt 1: Try AgentQL (Best data, but only 50 calls/mo).
    Attempt 2: Fallback to DuckDuckGo + Gemini (Unlimited, but messier).
    """
    
    # --- STRATEGY A: The "Luxury" Path (AgentQL) ---
    try:
        # Check if we have an API key configured
        if os.getenv("AGENTQL_API_KEY"):
            print(f"💎 Using AgentQL for {fabric_name}...")
            # ... AgentQL query logic ...
            # If successful, return data
            # return {"price": 20.00, "source": "AgentQL"}
            pass 
    except Exception as e:
        print(f"⚠️ AgentQL quota likely exceeded: {e}")

    # --- STRATEGY B: The "Free" Path (Playwright + Gemini) ---
    print(f"🔧 Falling back to Free Search for {fabric_name}...")
    
    # 1. Find URL via DuckDuckGo
    search_query = f"{fabric_name} fabric price per yard wholesale"
    with DDGS() as ddgs:
        # Get first result
        results = list(ddgs.text(search_query, max_results=1))
        if not results:
            return {"error": "No suppliers found"}
        target_url = results[0]['href']

    # 2. Scrape Text (Playwright)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(target_url, timeout=15000)
            text_content = page.inner_text("body")[:4000] # Cap text to save tokens
        except:
            return {"error": "Scraping failed"}
        finally:
            browser.close()

    # 3. Extract Price (Gemini Flash)
    time.sleep(SAFETY_DELAY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        f"Extract price from text: {text_content}. Return JSON: {{'price': float}}"
    )
    
    return {"price": response.text, "source": "FreeTier_Scraper"}

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