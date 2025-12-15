import streamlit as st
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

APP_NAME = "Atelier"
USER_ID = "local_user"

# --------------------------
# Helper functions (from run.py)
# --------------------------
def guess_mime(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "application/octet-stream"

def make_image_message(image_bytes: bytes, mime_type: str, prompt: str) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=prompt),
        ],
    )

def _extract_state(session) -> Dict[str, Any]:
    if hasattr(session, "state") and isinstance(session.state, dict):
        return session.state
    if hasattr(session, "context") and isinstance(session.context, dict):
        return session.context
    return {}

def _coerce_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}

def _get_agent_name(event) -> str:
    return getattr(event, "author", None) or getattr(event, "agent_name", None) or "unknown"

def _parse_event_parts(event) -> Tuple[List[Tuple[str, Any]], List[Tuple[str, Any]], List[str]]:
    calls, resps, texts = [], [], []
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content else None
    if not parts:
        return calls, resps, texts
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            texts.append(text)
        fn_call = getattr(part, "function_call", None)
        if fn_call:
            calls.append((getattr(fn_call, "name", None), getattr(fn_call, "args", None)))
        fn_resp = getattr(part, "function_response", None)
        if fn_resp:
            resps.append((getattr(fn_resp, "name", None), getattr(fn_resp, "response", None)))
    return calls, resps, texts

# --------------------------
# Async runner
# --------------------------
async def run_pipeline(image_bytes: bytes, mime_type: str, prompt: str, session_id: str):
    from src.executor import root_agent
    
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    
    events_log = []
    
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=make_image_message(image_bytes, mime_type, prompt),
    ):
        agent = _get_agent_name(event)
        calls, resps, texts = _parse_event_parts(event)
        events_log.append({"agent": agent, "calls": calls, "resps": resps, "texts": texts})
    
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    final_state = _extract_state(session)
    
    return events_log, final_state

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="Atelier - Fashion CFO", page_icon="👗", layout="wide")

st.title("👗 Atelier - AI Fashion CFO")
st.markdown("**Analyze garment profitability using multi-agent AI**")

# Architecture Section (Full Width)
with st.expander("🏗️ **System Architecture**", expanded=False):
    arch_image_path = Path("data/Architecture.png")
    if arch_image_path.exists():
        st.image(str(arch_image_path), caption="Multi-Agent Pipeline Architecture", use_container_width=True)
    else:
        st.info("Architecture diagram not found at `data/Architecture.png`")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key_status = "✅ Configured" if os.getenv("GOOGLE_API_KEY") else "❌ Missing"
    serpapi_status = "✅ Configured" if os.getenv("SERPAPI_API_KEY") else "❌ Missing"
    
    st.markdown(f"**Gemini API:** {api_key_status}")
    st.markdown(f"**SerpAPI:** {serpapi_status}")
    
    st.divider()
    st.header("📊 Target Settings")
    target_margin = st.slider("Target Profit Margin", 20, 60, 40, 5, format="%d%%")
    max_iterations = st.slider("Max Optimization Loops", 1, 5, 3)
    
    st.divider()
    st.markdown("### 🔄 Pipeline Flow")
    st.markdown("""
    1. **Analyzer** - Identify fabric & specs
    2. **Sourcer** - Find fabric prices
    3. **Market** - Research retail prices
    4. **Optimizer** - Calculate profitability
    """)

# --------------------------
# Upload Section
# --------------------------
st.header("📸 Upload Garment Image")

col_upload, col_preview = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "webp"])

with col_preview:
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Garment", width=200)

if uploaded_file:
    if st.button("🚀 Analyze Profitability", type="primary", use_container_width=True):
        # Get image data
        image_bytes = uploaded_file.getvalue()
        mime_type = f"image/{uploaded_file.type.split('/')[-1]}"
        if "jpeg" in uploaded_file.name.lower() or "jpg" in uploaded_file.name.lower():
            mime_type = "image/jpeg"
        
        prompt = "Analyze the garment in the image and save garment specs (fabric, yardage, complexity)."
        session_id = f"session_{uploaded_file.name}"
        
        # Run pipeline
        with st.spinner("🔄 Running multi-agent analysis..."):
            try:
                events_log, final_state = asyncio.run(
                    run_pipeline(image_bytes, mime_type, prompt, session_id)
                )
                st.session_state["events_log"] = events_log
                st.session_state["final_state"] = final_state
                st.success("✅ Analysis complete!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# --------------------------
# Results Section (Full Width)
# --------------------------
st.divider()
st.header("📊 Analysis Results")

if "final_state" in st.session_state:
    state = st.session_state["final_state"]
    
    # Top Row: Garment Analysis + Profitability Summary
    col1, col2 = st.columns([1, 1])
    
    # Garment Specs Card
    gs = state.get("garment_specs", {})
    with col1:
        st.subheader("👗 Garment Analysis")
        if gs:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Type:** {gs.get('garment_type', 'N/A')}")
                st.markdown(f"**Name:** {gs.get('garment_name', 'N/A')}")
                st.markdown(f"**Silhouette:** {gs.get('silhoutte', 'N/A')}")
                st.markdown(f"**Length:** {gs.get('length', 'N/A')}")
                st.markdown(f"**Sleeves:** {gs.get('sleeves', 'N/A')}")
            with c2:
                st.markdown(f"**Fabric:** {gs.get('primary_fabric', 'N/A')}")
                conf = float(gs.get('fabric_confidence', 0)) * 100
                st.markdown(f"**Confidence:** {conf:.0f}%")
                st.markdown(f"**Yardage:** {gs.get('estimated_yardage', 'N/A')} yards")
                st.markdown(f"**Complexity:** {gs.get('construction_complexity', 'N/A')}")
                st.markdown(f"**Neckline:** {gs.get('neckline', 'N/A')}")
        else:
            st.info("No garment data available")
    
    # Profit Analysis Card
    pa = state.get("profit_analysis", {})
    with col2:
        st.subheader("💰 Profitability")
        if pa:
            is_profitable = pa.get("is_profitable", False)
            margin = float(pa.get("profit_margin_percent", 0))
            
            if is_profitable:
                st.success(f"✅ **GREENLIGHT** - Profit Margin: {margin:.1f}%")
            else:
                st.warning(f"⚠️ **NEEDS OPTIMIZATION** - Profit Margin: {margin:.1f}%")
            
            # Progress bar for margin
            st.progress(min(margin / 100, 1.0))
            st.caption(f"Target: {pa.get('target_margin_percent', 40)}%")
            
            # Metrics row
            m1, m2 = st.columns(2)
            m1.metric("Total Cost", f"${float(pa.get('total_cost', 0)):.2f}")
            m2.metric("Profit", f"${float(pa.get('profit', 0)):.2f}", 
                     delta=f"{margin:.1f}%")
        else:
            st.info("No profitability data available")
    
    # Middle Row: Cost Breakdown
    st.subheader("💵 Cost & Revenue Breakdown")
    col_fabric, col_labor, col_market, col_profit = st.columns(4)
    
    fc = _coerce_json_dict(state.get("fabric_cost", {}))
    mp = _coerce_json_dict(state.get("market_price", {}))
    
    with col_fabric:
        st.markdown("**🧵 Fabric Cost**")
        if fc:
            fabric_total = float(fc.get('price_per_yard', 0)) * float(fc.get('yards_needed', 0))
            st.metric("Total", f"${fabric_total:.2f}")
            st.caption(f"{fc.get('fabric_name', 'N/A')}")
            st.caption(f"${float(fc.get('price_per_yard', 0)):.2f}/yard × {fc.get('yards_needed', 0)} yards")
        else:
            st.metric("Total", "$0.00")
    
    with col_labor:
        st.markdown("**👷 Labor Cost**")
        if pa:
            st.metric("Total", f"${float(pa.get('labor_cost', 0)):.2f}")
            st.caption("Based on garment type & complexity")
        else:
            st.metric("Total", "$0.00")
    
    with col_market:
        st.markdown("**📈 Selling Price**")
        if mp:
            st.metric("Average", f"${float(mp.get('average_price', 0)):.2f}")
            low = float(mp.get('price_range_low', 0))
            high = float(mp.get('price_range_high', 0))
            st.caption(f"Range: ${low:.2f} - ${high:.2f}")
            st.caption(f"Trend: {mp.get('trend_status', 'N/A')}")
        else:
            st.metric("Average", "$0.00")
    
    with col_profit:
        st.markdown("**💰 Net Profit**")
        if pa:
            profit = float(pa.get('profit', 0))
            margin = float(pa.get('profit_margin_percent', 0))
            st.metric("Profit", f"${profit:.2f}", delta=f"{margin:.1f}% margin")
        else:
            st.metric("Profit", "$0.00")
    
    # Bottom: Expandable Details (stacked vertically)
    st.divider()
    
    with st.expander("📜 **Agent Event Log**"):
        if "events_log" in st.session_state:
            for event in st.session_state["events_log"]:
                agent = event["agent"]
                for name, args in event["calls"]:
                    st.code(f"[{agent}] TOOL CALL: {name}")
                for name, resp in event["resps"]:
                    st.code(f"[{agent}] TOOL RESULT: {name}")
                for text in event["texts"]:
                    if text.strip():
                        st.text(f"[{agent}] {text[:150]}...")
    
    with st.expander("🔧 **Raw State (Debug)**"):
        st.json(state)

else:
    st.info("👆 Upload an image and click 'Analyze Profitability' to see results")

# Footer
st.divider()
st.markdown("Built with **Google ADK** • **Gemini 2.5** • **SerpAPI** | Hackathon Project")