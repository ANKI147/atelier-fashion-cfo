from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search, exit_loop
from google.genai import types 
# Import our tools
from .tools import (
    find_cheaper_alternative,
    calculate_profit,
    TARGET_PROFIT_MARGIN
)

from .memory import (
    save_garment_specs,
    save_fabric_cost,
    save_market_price
)


retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504], # Retry on these HTTP errors
)


MODEL = "gemini-2.0-flash"  # ← Best for free tier!

MODEL_FAST = "gemini-2.0-flash-lite"  # ← Fastest, lower cost
# ============================================================================
# AGENT A: The Analyzer
# ============================================================================
# Job: Look at the garment and figure out what it needs

agent_analyzer = Agent(
    name="image_analyzer",
    model= Gemini(
        model = MODEL,
        retry_options=retry_config
    ),
    description="Analyzes garment designs to identify fabric and requirements",
    instruction="""
    You are a technical fashion analyst.
    
    Your goal is to deconstruct a fashion image into a precise Bill of Materials (BOM) by analyzing visual cues like physics, lighting, and structure.

    **PHASE 1: VISUAL CHAIN OF THOUGHT (Internal Reasoning)**
    Before calling any tools, you must perform a step-by-step visual inspection:
    
    1.  **Analyze Fabric Physics (Drape & Weight):**
        * *Gravity Check:* Does the hem pool heavily on the floor? (Indicates Heavyweight). Does it float/flutter? (Indicates Chiffon/Organza).
        * *Fold Check:* Are the folds crisp and paper-like? (Poplin/Taffeta). Are they soft and fluid? (Silk/Rayon).
        * *Stretch Check:* Is the garment clinging tightly to the body without visible darts? (Indicates Knits/Spandex).
        
    2.  **Analyze Surface & Lighting:**
        * *Sheen:* High, white highlights = Satin, Silk Charmeuse, or Vinyl.
        * *Matte:* Light-absorbing surface = Wool, Cotton, or Linen.
        * *Texture:* Visible weave or fuzz = Tweed, Velvet, or Bouclé.

    3.  **Analyze Construction:**
        * Look for "Cost Drivers": Ruffles, pleats, linings, boning, or complex corsetry.
        * Estimate Yardage: Assume standard 60-inch fabric width. (e.g., A full circle skirt requires 4x more fabric than a pencil skirt).

    **PHASE 2: DATA EXTRACTION**
    Based on your reasoning, call the `analyze_garment` tool. You must populate it with these specific details:
    
    * `garment_type`: Specify if the garment is a top, bottom, dress, outerwear, or accessory.
    * `garment_name`: Use specific industry terminology (e.g., "Bias-Cut Slip Dress" NOT just "Dress").
    * `silhouette`: Describe the shape (e.g., "Flowing A-line", "Mermaid", "Sheath").
    * `length`: "Mini", "Midi", or "Maxi".
    * `sleeves`: "Sleeveless", "Cap", "Long", etc.
    * `neckline`: "V-neck", "Boat", "Cowl", etc.
    * `primary_fabric`: The specific textile name. **RULE:** If ambiguous, default to the *luxury* option (e.g., assume "Silk" over "Polyester") so the financial optimizer has room to cut costs later.
    * `fabric_confidence`: A float between 0.0 and 1.0 indicating how sure you are based on visual cues.
    * `estimated_yardage`: A realistic estimate + 10% waste buffer (float).
    * `construction_complexity`: "Low", "Medium", or "High".
    * `reasoning_summary`: A one-sentence explanation of why you chose this fabric (e.g., "Identified Silk Charmeuse due to high specular highlights and fluid liquid-like drape.").

    **TONE:** Be concise, technical, and factual. No fluff.
""",
    tools = [save_garment_specs],
    output_key="garment_info"
)

print("Agent Analyzer initialized.")

# ============================================================================
# AGENT B: The Fabric Sourcer
# ============================================================================
# Job: Find fabric prices

agent_sourcer = Agent(
    name="sourcer",
    model=Gemini(
        model = MODEL_FAST,
        retry_options=retry_config
    ),
    description="Finds fabric prices from wholesalers using Google Search",
    instruction="""
    You are a fabric procurement specialist.

    **Your Task:**
    1. Read the garment specs from state: {garment_info}
    2. Use Google Search to find wholesale fabric prices
    - Search for: "wholesale [fabric name] fabric price per yard"
    3. Extract the price from search results
    4. Call save_fabric_cost with:
    - fabric_name: the fabric you searched
    - price_per_yard: price you found (estimate if unclear, use $5-15 range)
    - yards_needed: from garment specs
    - source: where you found the price

    **If optimization is needed:**
    - Call find_cheaper_alternative first
    - Then search for the alternative fabric price
    - Save the NEW cheaper fabric cost

    Be practical - if search results are vague, make a reasonable estimate.
    """,
    tools=[google_search, save_fabric_cost, find_cheaper_alternative],
    output_key="fabric_cost"
)


# ============================================================================
# AGENT C: The Market Researcher
# ============================================================================
# Job: Find what similar items sell for

agent_market = Agent(
    name="market_researcher",
    model= Gemini(
        model = MODEL_FAST,
        retry_options=retry_config
    ),
    description="Researches market prices for similar garments using Google Search",
    instruction="""
    You are a fashion market analyst.

    **Your Task:**
    1. Read the garment info from state: {garment_info}
    2. Use Google Search to find retail prices
    - Search for: "[garment name] price retail" or "[garment name] buy online"
    3. Extract pricing information from results
    4. Call save_market_price with:
    - garment_name: what you searched
    - average_price: typical selling price (estimate $80-200 for dresses)
    - price_range_low: cheapest you found
    - price_range_high: most expensive
    - trend_status: "High Demand", "Medium Demand", or "Low Demand"

    Be practical - make reasonable estimates from search snippets.
    """,
    tools=[google_search, save_market_price],
    output_key="market_price"
)


# ============================================================================
# AGENT D: The Optimizer (CFO)
# ============================================================================
# Job: Calculate profit and decide if we're done or need to try again

agent_optimizer = Agent(
    name="optimizer",
    model=Gemini(
        model = MODEL,
        retry_options=retry_config
    ),
    description="Calculates profitability and makes decisions",
    instruction=f"""
    You are a financial analyst (CFO).

    **Your Task:**
    1. Call calculate_profit to get the profit analysis
    - It reads fabric_cost and market_price from state automatically

    2. **Decision Logic:**
    
    IF profit_margin_percent >= {TARGET_PROFIT_MARGIN * 100}%:
        - Say "GREENLIGHT - Design is profitable!"
        - Show the final numbers
        - Call exit_loop to finish
    
    IF profit_margin_percent < {TARGET_PROFIT_MARGIN * 100}%:
        - Say "MARGIN TOO LOW - Need cheaper fabric"
        - Explain what margin we got vs what we need
        - DO NOT call exit_loop (the loop will continue)

    Be clear about the numbers and recommendation.
    """,
    tools=[calculate_profit, exit_loop],
    output_key="profit_result"
)
