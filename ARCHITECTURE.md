
# Architecture Overview

Atelier is a multi-agent system designed to act as a "Virtual CFO" for fashion designers. It uses a hierarchical agent workflow to analyze images, source materials, research market data, and optimize profitability in a loop.

![Architecture diagram](data/Architecture.png)


## Components

### 1. User interface

- **CLI (Command Line Interface):** The entry point is `run.py`.
- Accepts arguments for image paths, prompts, and target margins.
- Features a custom `PipelinePrinter` class that renders structured, aesthetically formatted logs (ASCII boxes, tables) to the terminal for real-time feedback.

### 2. Agent core

- **Planner (`planner.py`):** Defines four specialized agents using the Google ADK:
  - **Analyzer:** A multimodal agent (Gemini 2.5 Pro) that extracts garment specifications (fabric, yardage, complexity) from images.
  - **Sourcer:** A research agent (Gemini 2.5 Flash) that finds wholesale fabric prices via Google Search.
  - **Market:** A research agent (Gemini 2.5 Flash) that finds competitor retail prices via SerpAPI.
  - **Optimizer:** A logic-heavy agent (Gemini 2.5 Pro) that calculates margins and decides whether to "Greenlight" the design or request changes (cheaper fabric/upgrade materials).
- **Executor (`executor.py`):** Orchestrates the agents using ADK patterns:
  - **SequentialAgent:** Runs the Analyzer first, followed by the Loop.
  - **ParallelAgent:** Runs the Sourcer and Market agents concurrently to reduce latency.
  - **LoopAgent:** Manages the optimization cycle, allowing the system to retry sourcing up to 3 times if profit targets aren't met.
- **Memory (`memory.py`):**
  - Uses `InMemorySessionService` to maintain session state.
  - **Shared state dictionary:** Stores critical data (`garment_specs`, `fabric_cost`, `market_price`, `profit_analysis`) accessible by all tools via `ToolContext`.

### 3. Tools / APIs

- **Google Gemini API:**
  - `gemini-2.5-pro`: Used for complex reasoning (vision analysis, financial optimization).
  - `gemini-2.5-flash`: Used for high-speed, parallel tasks (search queries).
- **External APIs:**
  - **SerpAPI (Google Shopping):** Fetches real-time retail pricing trends.
  - **Google Search:** Used by the Sourcer agent to find wholesale fabric suppliers.
- **Custom tools (`tools.py`):**
  - `calculate_profit`: Performs the financial math (labor + material vs. retail).
  - `save_garment_specs`: Structured data extraction tool.
  - `save_optimization_flag`: Controls the loop logic (continue vs. exit).

### 4. Observability

- **Event streaming:** The `run.py` script listens to the ADK event stream to capture every thought, tool call, and result.
- **Structured logging:**
  - **Raw output:** Prints raw tool inputs/outputs for debugging (`print_event_io`).
  - **User-facing output:** The `PipelinePrinter` consolidates complex JSON states into readable "Agent Completion Cards" (e.g., "AGENT B: FABRIC SOURCING COMPLETE").
  - **State tracking:** Prints the full JSON state at the end of execution for auditability.


