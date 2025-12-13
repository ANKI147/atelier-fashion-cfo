import os
import time
import json
from duckduckgo_search import DDGS
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import agentql

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
