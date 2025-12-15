# Atelier - AI-Powered Fashion CFO

**Automated profitability analysis for fashion designers using multi-agent AI**

Atelier analyzes garment images to determine manufacturing costs, market pricing, and profitability—helping fashion designers make data-driven business decisions before production.

## 🧪 Testing

**Try different garment types from the sample folder:**
```bash
# Elegant evening wear
python run.py --image data/garments/midi_satin_elegant_evening.jpg

# Casual wear
python run.py --image data/garments/mini_pleated_matte_casual.jpg

# Business attire
python run.py --image data/garments/hip_length_structured_business.jpg

# Traditional style
python run.py --image data/garments/maxi_flowy_chiffon_traditional.jpg
```

**Sample images are available in `data/garments/`**

---

## 🎯 What It Does

Upload a garment image → Get instant profitability analysis:

1. **Image Analysis** - Identifies fabric type, construction details, yardage
2. **Cost Research** - Searches wholesale fabric suppliers for current pricing  
3. **Market Analysis** - Finds retail prices for similar garments via Google Shopping
4. **Profit Calculation** - Determines if the design meets ~40% target profit margin (±20% acceptable range)

---

## 🏗️ Architecture

**Multi-Agent System** powered by Google ADK:

```
📸 Garment Image
    ↓
🤖 Agent A (Analyzer) [Gemini 2.5 Pro]
    → Analyzes: fabric, silhouette, yardage, construction complexity
    ↓
🔄 Optimization Loop (max 3 iterations)
    ↓
🤖 Agent B (Sourcer) + 🤖 Agent C (Market) ← Run in Parallel [Gemini 2.5 Flash]
    → Searches: fabric prices (Google Search) + retail prices (SerpAPI Shopping)
    ↓
🤖 Agent D (Optimizer) [Gemini 2.5 Pro]
    → Calculates: profit margin (fabric + labor costs)
    → Decision: GREENLIGHT ✅ | MARGIN TOO LOW ⚠️ | MARGIN TOO HIGH ⬆️
    ↓
📊 Final Report: Cost breakdown + Profitability verdict
```

**Key Features:**
- **Parallel Execution**: Fabric sourcing and market research run simultaneously
- **Iterative Optimization**: Automatically finds cheaper/premium alternatives based on margin
- **Real Data**: Live Google Search + SerpAPI Google Shopping for current pricing
- **Smart Labor Estimation**: Calculates labor costs based on garment type and complexity

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file:

```env
# Google Gemini API (required)
GOOGLE_API_KEY="your-gemini-key"

# SerpAPI for Google Shopping market research (required)
SERPAPI_API_KEY="your-serpapi-key"
```

**Get API Keys:**
- Gemini: https://aistudio.google.com/
- SerpAPI: https://serpapi.com/ (100 searches/month free)

**Optional: Multiple API Keys**

For higher throughput, you can provide multiple Gemini keys:
```env
GOOGLE_API_KEYS="key1,key2,key3"
```

### 3. Run Analysis

#### Option A: Web Interface (Recommended for Demos)
```bash
streamlit run app.py
```
Opens at http://localhost:8501 with a visual interface for uploading images and viewing results.

#### Option B: Command Line
```bash
python run.py --image data/garments/your_garment_image.jpg
```

**CLI Options:**
```bash
python run.py --image <path>              # Required: path to garment image
              --prompt <text>             # Optional: custom analysis prompt
              --session-id <id>           # Optional: session identifier
              --max-iterations <n>        # Optional: max optimization loops (default: 3)
              --target-margin <float>     # Optional: target profit margin (default: 0.40)
```

**Example:**
```bash
python run.py --image data/garments/midi_satin_elegant_evening.jpg
```

---

## 📁 Project Structure

```
Atelier/
├── app.py                      # Streamlit web interface
├── run.py                      # CLI entry point
├── .env                        # API keys configuration
├── requirements.txt            # Python dependencies
│
├── src/                        # Core application code
│   ├── __init__.py            # Package exports
│   ├── agent.py               # Root agent export
│   ├── planner.py             # AI agent definitions (Analyzer, Sourcer, Market, Optimizer)
│   ├── executor.py            # Multi-agent workflow orchestration (Sequential, Parallel, Loop)
│   ├── tools.py               # Profit calculation, SerpAPI integration
│   └── memory.py              # Agent state management (garment specs, optimization flags)
│
└── data/garments/              # Sample garment images for testing
```

---

## 🤖 Agent Details

| Agent | Model | Role | Tools |
|-------|-------|------|-------|
| **Analyzer** | Gemini 2.5 Pro | Visual fabric analysis, BOM extraction | `save_garment_specs`, `save_optimization_flag` |
| **Sourcer** | Gemini 2.5 Flash | Wholesale fabric price research | `google_search` |
| **Market** | Gemini 2.5 Flash | Retail market price research | `serpapi_google_shopping_market_price` |
| **Optimizer** | Gemini 2.5 Pro | Profitability calculation & decisions | `calculate_profit`, `save_optimization_flag`, `exit_loop` |

---

## 💰 Profit Logic

**Target Margin:** 40% (configurable in `tools.py`)

**Decision Flow:**
- ✅ **GREENLIGHT** (20%-60% margin): Design is profitable, proceed
- ⚠️ **MARGIN TOO LOW** (<20%): Loop back, search for cheaper fabric
- ⬆️ **MARGIN TOO HIGH** (>50%): Loop back, upgrade to premium materials

**Cost Calculation:**
- Fabric Cost = price_per_yard × yards_needed
- Labor Cost = estimated hours × $10/hour (based on garment type & complexity)
- Total Cost = Fabric + Labor
- Profit Margin = (Selling Price - Total Cost) / Selling Price

---

## 🔧 Technical Details

**AI Models:**
- Primary Analysis: `gemini-2.5-pro` (complex reasoning)
- Fast Research: `gemini-2.5-flash` (parallel searches)

**Frameworks & APIs:**
- Google ADK (Agent Development Kit) - Multi-agent orchestration
- Google Gemini API - Vision and language models
- SerpAPI - Google Shopping price data
- Google Search - Fabric wholesale pricing

**Agent Patterns Used:**
- `SequentialAgent` - Main pipeline orchestration
- `ParallelAgent` - Concurrent fabric + market research
- `LoopAgent` - Iterative optimization (max 3 iterations)

---

## 📊 Use Cases

**For Fashion Designers:**
- Pre-production profitability checks
- Alternative fabric sourcing recommendations
- Pricing strategy optimization

**For Fashion Schools:**
- Teaching cost-conscious design principles
- Business planning for student projects

**For Small Brands:**
- Fast market validation
- Competitive pricing analysis

---

## 🔍 Garment Specs Captured

The Analyzer agent extracts:
- `garment_type`: top, bottom, dress, outerwear, accessory
- `garment_name`: Specific industry terminology
- `silhouette`: Shape description (A-line, Mermaid, Sheath, etc.)
- `length`: Mini, Midi, Maxi
- `sleeves`: Sleeveless, Cap, Long, etc.
- `neckline`: V-neck, Boat, Cowl, etc.
- `primary_fabric`: Identified textile (defaults to luxury option if ambiguous)
- `fabric_confidence`: 0.0-1.0 confidence score
- `estimated_yardage`: Yards needed + 10% waste buffer
- `construction_complexity`: Low, Medium, High

---

## 📝 License

MIT License - See LICENSE file

---

## 🤝 Team

Built for the Agentic AI App Hackathon

**Tech Stack:** Google Gemini API • Google ADK • SerpAPI • Python
