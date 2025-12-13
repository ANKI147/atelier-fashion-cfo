from google.adk.agents import LlmAgent
from google.adk.tools import exit_loop

# Import our tools
from .tools import (
    analyze_garment,
    get_fabric_price,
    get_market_price,
    find_cheaper_fabric,
    calculate_profit,
    TARGET_PROFIT_MARGIN
)

# ============================================================================
# CONFIGURATION - FREE TIER MODELS (December 2025)
# ============================================================================
# 
# AVAILABLE FREE MODELS:
# ─────────────────────────────────────────────────────────────────────────
# "gemini-2.0-flash"       → Best choice! Fast, free, good for agents
# "gemini-2.5-flash"       → Newer, has "thinking" capability  
# "gemini-2.5-flash-lite"  → Fastest & cheapest, less capable
# "gemini-2.5-pro"         → Most powerful but very limited (5 RPM)
# ─────────────────────────────────────────────────────────────────────────
#
# RECOMMENDATION: Use gemini-2.0-flash for hackathon demos
# It's fast, reliable, and has generous free limits!

MODEL = "gemini-2.0-flash"  # ← Best for free tier!

MODEL-FAST = "gemini-2.0-flash-lite"  # ← Fastest, lower cost
# ============================================================================
# AGENT A: The Analyzer
# ============================================================================
# Job: Look at the garment and figure out what it needs

agent_analyzer = LlmAgent(
    name="analyzer",
    model=MODEL,
    description="Analyzes garment images to identify fabric and requirements",
    instruction="""
    You are a technical fashion analyst.
    
    INPUT: You will receive a file path to an image (e.g., 'images/dress_01.jpg').
    
    YOUR JOB:
    1. Call the `analyze_garment(image_path)` tool with this exact path.
    2. The tool will return a JSON object with fabric, yards, and type.
    3. Output this JSON strictly so the next agent can use it.
    """,
    tools=[analyze_garment],
    output_key="garment_info"
)


# ============================================================================
# AGENT B: The Fabric Sourcer
# ============================================================================
# Job: Find fabric prices

agent_sourcer = LlmAgent(
    name="sourcer",
    model=MODEL,
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

agent_market = LlmAgent(
    name="market_researcher",
    model=MODEL,
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

agent_optimizer = LlmAgent(
    name="optimizer",
    model=MODEL,
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
