# Technical Explanation

## 1. Agent Workflow

Step-by-step processing of a garment image input:

1. **Receive User Input**
   - `run.py` accepts garment image path via `--image` argument
   - Image is converted to base64 with MIME type detection
   - Wrapped in `types.Content` message with analysis prompt

2. **Agent A: Image Analysis (Sequential)**
   - Gemini 2.5 Pro analyzes fabric physics, surface lighting, and construction
   - Uses ReAct pattern: Thought → Action → Observation → Final
   - Calls `save_garment_specs` to persist analysis to memory
   - Calls `save_optimization_flag("initial")` to initialize loop state

3. **Optimization Loop (Max 3 Iterations)**
   
   3a. **Agents B & C: Parallel Research**
   - **Sourcer (B):** Reads `garment_specs` from memory, searches Google for wholesale fabric prices
   - **Market (C):** Reads `garment_specs` from memory, calls SerpAPI for retail market prices
   - Both run concurrently and write results to memory

   3b. **Agent D: Profit Calculation & Decision**
   - Calls `calculate_profit` tool (reads `fabric_cost` + `market_price` from memory)
   - Applies decision logic:
     - Margin 20-60% → GREENLIGHT → call `exit_loop`
     - Margin < 20% → Set flag to "needed" → loop continues (find cheaper fabric)
     - Margin > 60% → Set flag to "needed" → loop continues (upgrade materials)

4. **Return Final Output**
   - Final state dumped as JSON with all analysis results
   - `PipelinePrinter` displays structured completion cards for each agent

---

## 2. Key Modules

### Planner (`planner.py`)
Defines the four AI agents with their configurations:
- **agent_analyzer:** Gemini 2.5 Pro, visual fabric analysis, tools: `save_garment_specs`, `save_optimization_flag`
- **agent_sourcer:** Gemini 2.5 Flash, fabric price search, tools: `google_search`
- **agent_market:** Gemini 2.5 Flash, market research, tools: `serpapi_google_shopping_market_price`
- **agent_optimizer:** Gemini 2.5 Pro, profit calculation, tools: `calculate_profit`, `save_optimization_flag`, `exit_loop`

Includes retry configuration: 5 attempts, exponential backoff, handles HTTP 429/500/503/504.

### Executor (`executor.py`)
Orchestrates agent workflow using ADK patterns:
- **parallel_research:** `ParallelAgent` running sourcer + market concurrently
- **optimization_loop:** `LoopAgent` with `max_iterations=3`, contains parallel_research → optimizer
- **root_agent:** `SequentialAgent` running analyzer → optimization_loop

### Memory Store (`memory.py`)
Provides tools for persisting data to `ToolContext.state`:
- **save_garment_specs():** Saves 10 garment attributes (type, name, fabric, yardage, complexity, etc.)
- **save_optimization_flag():** Sets `needs_optimization` to "initial", "needed", or "not needed"

---

## 3. Tool Integration

| Tool | API/Source | Function Call | Purpose |
|------|------------|---------------|---------|
| `google_search` | Google ADK built-in | `google_search(query)` | Search wholesale fabric prices |
| `serpapi_google_shopping_market_price` | SerpAPI | `serpapi_google_shopping_market_price(garment_query)` | Fetch retail prices from Google Shopping |
| `calculate_profit` | Custom (tools.py) | `calculate_profit(tool_context)` | Compute costs, profit, margin from state |
| `save_garment_specs` | Custom (memory.py) | `save_garment_specs(garment_type, ...)` | Persist garment analysis to state |
| `save_optimization_flag` | Custom (memory.py) | `save_optimization_flag(needs_optimization)` | Control loop continuation |
| `exit_loop` | Google ADK built-in | `exit_loop()` | Terminate optimization loop early |

**External API Configuration (.env):**
```
GOOGLE_API_KEY=your-gemini-key
SERPAPI_API_KEY=your-serpapi-key
```

---

## 4. Observability & Testing

### Logging
The `PipelinePrinter` class in `run.py` provides real-time structured logging:

- **Event Stream Processing:** Every tool call/result/text output is logged with agent name
- **Deduplication:** Tracks fingerprints to prevent duplicate output across iterations
- **Structured Cards:** Box-formatted completion summaries for each agent stage

**Sample Output:**
```
[image_analyzer] TOOL CALL: save_garment_specs({...})
[image_analyzer] TOOL RESULT: save_garment_specs: ✅ Specs saved...

╔══════════════════════════════════════════════════════════════╗
║           AGENT A: GARMENT DECONSTRUCTION COMPLETE           ║
╚══════════════════════════════════════════════════════════════╝
 IDENTIFICATION:
   Type:       dress
   Name:       Bias-Cut Slip Dress
   ...
```

### Testing
Run analysis on sample images:
```bash
# Basic test
python run.py --image data/garments/midi_satin_elegant_evening.jpg

# With custom parameters
python run.py --image data/garments/mini_pleated_matte_casual.jpg \
              --max-iterations 3 \
              --target-margin 0.40
```

**Final State Output:** Complete JSON dump of all state keys at pipeline end for verification.

---

## 5. Known Limitations

| Category | Limitation | Impact |
|----------|------------|--------|
| **Fabric Identification** | Visual ambiguity between similar fabrics (silk vs polyester satin) | May misestimate costs |
| **Fabric Identification** | Cannot detect fabric blends from image alone | Assumes single primary fabric |
| **Pricing Data** | Google Search results vary by region and time | Inconsistent fabric prices |
| **Pricing Data** | SerpAPI returns retail prices, not wholesale | Market prices may be inflated |
| **Labor Estimation** | Fixed $10/hour rate, simplified complexity model | May not reflect actual regional costs |
| **Loop Behavior** | Max 3 iterations may not find optimal solution | Could exit without meeting target |
| **Loop Behavior** | No backtracking if material upgrade overshoots margin | May oscillate between too high/low |
| **API Dependencies** | Requires valid Gemini API key | Fails without credentials |
| **API Dependencies** | SerpAPI rate limit (100 free searches/month) | Market research may fail if exhausted |
| **Output Parsing** | Agents must output strict JSON-like format | Malformed LLM output breaks downstream parsing |
| **Ambiguous Inputs** | Low-quality or unusual garment images | Lower fabric_confidence, potential misidentification |
