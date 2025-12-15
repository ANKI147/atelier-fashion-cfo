from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search, exit_loop
from google.genai import types 
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Import our tools
from .tools import (
    calculate_profit,
    serpapi_google_shopping_market_price
)

from .memory import (
    save_garment_specs,
    save_optimization_flag
)


retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504], # Retry on these HTTP errors
)


MODEL = "gemini-2.5-pro" 

MODEL_FAST = "gemini-2.5-flash" 


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

    Use a ReAct-style workflow:
    - Thought: Briefly note what you will infer next (keep it short; no long chain-of-thought).
    - Action: Call a tool (save_garment_specs, save_optimization_flag) with the required fields.
    - Observation: Read the tool result and verify the state was saved.
    - Final: Output a concise garment_info summary (2–4 sentences) so output_key="garment_info" is always populated.

    THOUGHT (visual inspection checklist; keep it brief)
    1) Fabric physics (drape/weight):
    - Gravity check: pooling hem => heavyweight; floating/flutter => chiffon/organza.
    - Fold check: crisp folds => poplin/taffeta; fluid folds => silk/rayon.
    - Stretch check: clinging without darts => knits/spandex.

    2) Surface & lighting:
    - Sheen: bright highlights => satin/silk charmeuse/vinyl.
    - Matte: light-absorbing => wool/cotton/linen.
    - Texture: visible weave/fuzz => tweed/velvet/bouclé.

    3) Construction:
    - Identify cost drivers (ruffles, pleats, linings, boning, corsetry).
    - Estimate yardage assuming 60-inch width (include ~10% waste buffer).

    ACTION: Call the tool save_garment_specs with these fields:
    Based on your reasoning, call the `save_garment_specs` tool. You must populate the garment_info ouput with a summary of the details below : 
    
    * garment_type: Specify if the garment is a top, bottom, dress, outerwear, or accessory.
    * garment_name: Use specific industry terminology (e.g., "Bias-Cut Slip Dress" NOT just "Dress").
    * silhoutte: Describe the shape (e.g., "Flowing A-line", "Mermaid", "Sheath").
    * length: "Mini", "Midi", or "Maxi".
    * sleeves: "Sleeveless", "Cap", "Long", etc.
    * neckline: "V-neck", "Boat", "Cowl", etc.
    * primary_fabric: The specific textile name. **RULE:** If ambiguous, default to the *luxury* option (e.g., assume "Silk" over "Polyester") so the financial optimizer has room to cut costs later.
    * fabric_confidence: A float between 0.0 and 1.0 indicating how sure you are based on visual cues.
    * estimated_yardage: A realistic estimate + 10% waste buffer (float).
    * construction_complexity: "Low", "Medium", or "High".
    * reasoning_summary: A one-sentence explanation of why you chose this fabric (e.g., "Identified Silk Charmeuse due to high specular highlights and fluid liquid-like drape.").
    
    OBSERVATION 1
    Confirm the tool result indicates specs were saved successfully.

    ACTION 2 (must do)
    Call save_optimization_flag with:
    - needs_optimization = "initial"

    OBSERVATION 2
    Confirm the tool result indicates the optimization flag was saved.

    FINAL (must do; this becomes garment_info)
    Write a concise summary including:
    - garment_type, garment_name, silhoutte, length
    - sleeves, neckline
    - primary_fabric + fabric_confidence
    - estimated_yardage + construction_complexity
    - reasoning_summary (one sentence on why you chose the fabric)

    TONE: Be concise, technical, and factual. No fluff.

    """,
    tools = [save_garment_specs, save_optimization_flag],
    output_key="garment_info"
)

print("Agent Analyzer initialized.")



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
    1. Read the [garment_info] from the previous agent and specs from state:  {garment_specs}.
    2. Use Google Search to find wholesale fabric prices
    - Search for: "wholesale [fabric name] fabric price per yard".
    3. Extract the price from search results.

    Check if the state key "needs_optimization" is set to "needed":
    if yes then proceed with the following instructions for optimization:
    **YOUR TASK FOR OPTIMIZATION WHEN LOOPING:**

    Check if the state key "needs_optimization" is set to "needed":

    If YES, decide what to do using the latest optimizer output :

    - If a state key names profit_result exists and contains the phrase "MARGIN TOO HIGH":
    Your task is to find a HIGHER QUALITY / HIGHER COST fabric (upgrade materials).
    Search examples:
    - "premium wholesale [current_fabric] fabric price per yard"
    - "Italian [current_fabric] suiting price per yard"
    - "wool cashmere blend suiting price per yard"
    - "100% silk [fabric] price per yard"
    Pick a higher quality option that plausibly costs more than the current one.

    - Otherwise (default when margin was low or profit_result is missing):
    
        your task is to find a LOWER price for the CURRENT fabric.:
    - Identify the current_fabric and its source from {garment_specs}.
    - use Google Search to find a source for the current fabric at a LOWER price.
    - Search for: "cheap wholesale [current_fabric] fabric price per yard".
    - if you're unable to find a lower price, suggest a cheaper ALTERNATIVE fabric instead by 
        using Google search to find a affordable fabric that could substitute the current one.
    - Search for: "wholesale [alternative_fabric] fabric price per yard".

   

    4. **FINAL ANSWER FORMAT (MANDATORY)**  
    Return **only** a string of this format with exactly these keys:
    - `fabric_name`: the fabric you searched. (use the alternative if you switched)
    - `price_per_yard`: numeric price you found (estimate if unclear, use 5–15 range).
    - `yards_needed`: numeric value from garment specs.
    - `source`: short string describing where you found the price.
    Example of the required style (structure only):
    {"fabric_name": "Wool Suiting", "price_per_yard": 16.0,
      "yards_needed": 2.8, "source": "Fashion Fabrics Club"}

      Don't output anything else.

    Rules:
    - The final response must be a single line starting with `{` and ending with `}`.
    - Do **not** include backticks,backslashes ,Markdown, code fences, or the word "json".
    - Do **not** add explanations, prose, or extra keys.
    - Example of the required style (structure only):
    {"fabric_name": "Wool Suiting", "price_per_yard": 16.0, "yards_needed": 2.75, "source": "Fashion Fabrics Club"}
    Be practical - if search results are vague, make a reasonable estimate.
    """,
    tools=[google_search],
    output_key="fabric_cost"
)



agent_market = Agent(
    name="market_researcher",
    model= Gemini(
        model = MODEL_FAST,
        retry_options=retry_config
    ),
    description="Researches market prices for similar garments using serpapi",
    instruction="""
    You are a fashion market analyst.

    **Your Task:**
    1. Read the [garment_info] from the previous agent and specs from state:  {garment_specs}.
    2. Call the ONLY the tool serpapi_google_shopping_market_price to find retail prices
    - use [garement_name] from {garment_specs} as the [garment_query] for the tool serpapi_google_shopping_market_price .
    3. Extract pricing information from results.

    4. **FINAL ANSWER FORMAT (MANDATORY)**  
    Return **only** as a string of this format with exactly these keys:
    - `garment_name`: what you searched.
    - `average_price`: typical selling price (estimate 80–200 for dresses).
    - `price_range_low`: lowest price you found.
    - `price_range_high`: highest price you found.
    - `trend_status`: one of "High Demand", "Medium Demand", or "Low Demand".
      - Example of the required style (structure only):
    {"garment_name": "Glen Plaid Sheath Dress", "average_price": 165.0,
    "price_range_low": 79.99, "price_range_high": 280.0, "trend_status": "Medium Demand"}

    Don't output anything else.

    Rules:
    - The final response must be a single line starting with `{` and ending with `}`.
    - Do **not** include backticks, backslashes , Markdown, code fences, or the word "json".
    - Do **not** add explanations, prose, or extra keys.
  

    Be practical – make reasonable estimates from search snippets.
    """,
    tools=[serpapi_google_shopping_market_price],
    output_key="market_price"
)



agent_optimizer = Agent(
    name="optimizer",
    model=Gemini(
        model = MODEL,
        retry_options=retry_config
    ),
    description="Calculates profitability and makes decisions",
    instruction="""
    You are a financial analyst (CFO).

    **Your Task:**
    1. Call calculate_profit to get the profit analysis
    - It reads fabric_cost and market_price from state automatically

    2. **Decision Logic:**

    
    
    IF {TARGET_PROFIT_MARGIN * 100 +20}% >= profit_margin_percent >= {target_margin_percent * 100 -20}%:
        - Say "GREENLIGHT - Design is profitable!"
        - Show the final numbers
        - call the tool save_optimization_flag to set the key "needs_optimization" to the value "not needed" in state.
        - Call exit_loop to finish
        - Provide a brief summary of why and how the design is profitable in the profit_result output.

    
    IF profit_margin_percent < {target_margin_percent * 100}%:
        - your output must be a string "MARGIN TOO LOW - Need cheaper fabric" 
        - Explain what margin we got vs what we need
        - call the tool save_optimization_flag to set the key "needs_optimization" to the value "needed" in state.
        - DO NOT call exit_loop (the loop will continue)

    IF profit_margin_percent > {target_margin_percent * 100 + 10}%:
        - your output must be a string "MARGIN TOO HIGH - Upgrade materials" in profit_result
        - Briefly state current margin vs desired band (TARGET +/- 10%)
        - call save_optimization_flag to set "needs_optimization" to "needed"
        - DO NOT call exit_loop


    Be clear about the numbers and recommendation.
    """,
    tools=[calculate_profit, save_optimization_flag,exit_loop],
    output_key="profit_result"
)
