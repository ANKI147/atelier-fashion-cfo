from google.adk.agents import Agent
from google.adk.models.google_llm import GEMINI
from google.adk.runners import InMemoryRunner
from google.adk.tools import exit_loop
from google.genai import types 
# Import our tools
from .tools import (
    analyze_garment,
    get_fabric_price,
    get_market_price,
    find_cheaper_fabric,
    calculate_profit,
    TARGET_PROFIT_MARGIN
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
    name="Image Analyzer Agent",
    model= GEMINI(
        model = MODEL,
        retry_options=retry_config
    ),
    description="Analyzes garment designs to identify fabric and requirements",
    instruction="""
    You are a fashion design analyst.
    
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
    tools=[analyze_garment],
    output_key="garment_info"  # Saves result for other agents
)

print("Agent Analyzer initialized.")

# ============================================================================
# AGENT B: The Fabric Sourcer
# ============================================================================
# Job: Find fabric prices

agent_sourcer = Agent(
    name="sourcer",
    model=GEMINI(
        model = MODEL_FAST,
        retry_options=retry_config
    ),
    description="Finds fabric prices from wholesalers",
    instruction="""
    You are a fabric procurement specialist.
    
    Using the garment info from {garment_info}:
    1. Use get_fabric_price to find the cost
    2. If optimization is needed, use find_cheaper_fabric
    
    Report the total fabric cost.
    """,
    tools=[get_fabric_price, find_cheaper_fabric],
    output_key="fabric_cost"
)


# ============================================================================
# AGENT C: The Market Researcher
# ============================================================================
# Job: Find what similar items sell for

agent_market = Agent(
    name="market_researcher",
    model= GEMINI(
        model = MODEL_FAST,
        retry_options=retry_config
    ),
    description="Researches market prices for similar garments",
    instruction="""
    You are a market research analyst.
    
    Using the garment info from {garment_info}:
    1. Use get_market_price to find competitor prices
    2. Report the average selling price
    """,
    tools=[get_market_price],
    output_key="market_price"
)


# ============================================================================
# AGENT D: The Optimizer (CFO)
# ============================================================================
# Job: Calculate profit and decide if we're done or need to try again

agent_optimizer = Agent(
    name="optimizer",
    model=GEMINI(
        model = MODEL,
        retry_options=retry_config
    ),
    description="Calculates profitability and makes decisions",
    instruction=f"""
    You are a financial analyst (CFO).
    
    Using:
    - Fabric cost from {{fabric_cost}}
    - Market price from {{market_price}}
    
    Your job:
    1. Use calculate_profit to check profitability
    2. If profit margin >= {TARGET_PROFIT_MARGIN * 100}%:
       - Say "GREENLIGHT - Proceed with production!"
       - Call exit_loop to finish
    3. If profit margin < {TARGET_PROFIT_MARGIN * 100}%:
       - Say "Need to find cheaper fabric"
       - DO NOT call exit_loop (loop will continue)
    """,
    tools=[calculate_profit, exit_loop],
    output_key="profit_result"
)


