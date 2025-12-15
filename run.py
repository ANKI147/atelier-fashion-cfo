import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

APP_NAME = "Atelier"
USER_ID = "local_user"

print("SERPAPI_API_KEY present:", bool(os.getenv("SERPAPI_API_KEY")))


# --------------------------
# Formatting helpers
# --------------------------
def hr(title: str, width: int = 70) -> str:
    line = "=" * width
    return f"{line}\n {title}\n{line}"


def box(title: str, width: int = 62) -> str:
    top = "╔" + ("═" * width) + "╗"
    mid = "║" + title.center(width) + "║"
    bot = "╚" + ("═" * width) + "╝"
    return f"{top}\n{mid}\n{bot}"


def money(x: Any) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def pct(x: Any) -> str:
    try:
        return f"{float(x):.1f}%"
    except Exception:
        return "0.0%"


# --------------------------
# Content helpers
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


def make_image_message(image_path: Path, prompt: str) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=image_path.read_bytes(), mime_type=guess_mime(image_path)),
            types.Part.from_text(text=prompt),
        ],
    )


def _extract_state(session) -> Dict[str, Any]:
    # ADK session objects vary by version; try common patterns.
    if hasattr(session, "state") and isinstance(session.state, dict):
        return session.state
    if hasattr(session, "context") and isinstance(session.context, dict):
        return session.context
    return {}


def _jsonable(v: Any) -> Any:
    try:
        json.dumps(v)
        return v
    except Exception:
        return str(v)


def _coerce_json_dict(value: Any) -> Dict[str, Any]:
    # fabric_cost / market_price are JSON strings in your pipeline.
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
    """
    Returns (function_calls, function_responses, texts)
    where each call/resp is (name, payload).
    """
    calls: List[Tuple[str, Any]] = []
    resps: List[Tuple[str, Any]] = []
    texts: List[str] = []

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


def print_event_io(agent_name: str, calls, resps, texts) -> None:
    # Tool calls
    for name, args in calls:
        print(f"\n[{agent_name}] TOOL CALL: {name}({_jsonable(args)})")

    # Tool results
    for name, resp in resps:
        print(f"\n[{agent_name}] TOOL RESULT: {name}: {_jsonable(resp)}")

    # Text output
    for t in texts:
        print(f"\n[{agent_name}] OUTPUT:\n{t}")


# --------------------------
# Structured pipeline printer (no repeats)
# --------------------------
class PipelinePrinter:
    def __init__(self, image_name: str, target_margin: float, max_iterations: int, key_count: int):
        self.image_name = image_name
        self.target_margin = target_margin
        self.max_iterations = max_iterations
        self.key_count = key_count

        self.iteration = 0
        self.printed_a = False

        self.last_fabric_cost_raw: Optional[str] = None
        self.last_market_price_raw: Optional[str] = None
        self.last_profit_analysis_fingerprint: Optional[str] = None

    def print_banner(self) -> None:
        print(hr("VIRTUAL CFO - MULTI-AGENT PIPELINE"))
        print(f" Image: {self.image_name}")
        print(f" Target Margin: {int(self.target_margin * 100)}%")
        print(f" Max Iterations: {self.max_iterations}")
        print(f" Loaded {self.key_count} Gemini API key(s)")
        print("=" * 70)

    def maybe_print_agent_a_complete(self, state: Dict[str, Any], resps: List[Tuple[str, Any]]) -> None:
        if self.printed_a:
            return

        # Print only after save_garment_specs tool response (prevents duplicates)
        if not any(name == "save_garment_specs" for name, _ in resps):
            return

        gs = state.get("garment_specs") or {}
        if not gs:
            return

        print("\n" + box("AGENT A: GARMENT DECONSTRUCTION COMPLETE"))
        print(" IDENTIFICATION:")
        print(f"   Type:       {gs.get('garment_type')}")
        print(f"   Name:       {gs.get('garment_name')}")
        print(f"   Silhouette: {gs.get('silhoutte')}")
        print(f"   Length:     {gs.get('length')}")
        print(f"   Sleeves:    {gs.get('sleeves')}")
        print(f"   Neckline:   {gs.get('neckline')}")
        print(" FABRIC ANALYSIS:")
        print(f"   Primary Fabric:  {gs.get('primary_fabric')}")
        try:
            print(f"   Confidence:      {int(float(gs.get('fabric_confidence', 0)) * 100)}%")
        except Exception:
            print("   Confidence:      0%")
        print(f"   Estimated Yards: {gs.get('estimated_yardage')} yards")
        print(" CONSTRUCTION:")
        print(f"   Complexity: {gs.get('construction_complexity')}")
        print(" State updated: garment_specs set")

        self.printed_a = True

    def maybe_print_agent_b_complete(self, state: Dict[str, Any]) -> None:
        raw = state.get("fabric_cost")
        if not raw or raw == self.last_fabric_cost_raw:
            return

        # New fabric_cost implies a new sourcer result; also helps detect iteration boundaries
        if self.iteration == 0:
            self.iteration = 1
            print(hr(f"OPTIMIZATION ITERATION {self.iteration}/{self.max_iterations}"))
        else:
            self.iteration += 1
            if self.iteration <= self.max_iterations:
                print(hr(f"OPTIMIZATION ITERATION {self.iteration}/{self.max_iterations}"))

        fc = _coerce_json_dict(raw)
        total_cost = float(fc.get("price_per_yard", 0) or 0) * float(fc.get("yards_needed", 0) or 0)

        print(hr("AGENT B: FABRIC SOURCING"))
        gs = state.get("garment_specs") or {}
        print(f" Searching for: {gs.get('primary_fabric')}")

        print("\n" + box("AGENT B: FABRIC SOURCING COMPLETE"))
        print(" FABRIC SOURCED:")
        print(f"   Name:         {fc.get('fabric_name')}")
        print(f"   Price/Yard:   {money(fc.get('price_per_yard'))}")
        print(f"   Yards Needed: {fc.get('yards_needed')} yards")
        print(f"   Total Cost:   {money(total_cost)}")
        print(" SOURCE:")
        print(f"   {fc.get('source')}")
        print(" State updated: fabric_cost set")

        self.last_fabric_cost_raw = raw

    def maybe_print_agent_c_complete(self, state: Dict[str, Any]) -> None:
        raw = state.get("market_price")
        if not raw or raw == self.last_market_price_raw:
            return

        mp = _coerce_json_dict(raw)

        print(hr("AGENT C: MARKET RESEARCH"))
        gs = state.get("garment_specs") or {}
        print(f" Researching market for: {gs.get('garment_name')}")

        print("\n" + box("AGENT C: MARKET RESEARCH COMPLETE"))
        print(" MARKET ANALYSIS:")
        print(f"   Garment:      {mp.get('garment_name')}")
        print(" PRICING:")
        print(f"   Average:      {money(mp.get('average_price'))}")
        print(f"   Range:        {money(mp.get('price_range_low'))} - {money(mp.get('price_range_high'))}")
        print(" MARKET TREND:")
        print(f"   Status:       {mp.get('trend_status')}")
        print(" State updated: market_price set")

        self.last_market_price_raw = raw

    def maybe_print_agent_d_complete(self, state: Dict[str, Any], resps: List[Tuple[str, Any]]) -> None:
        # Critical gating: print only when calculate_profit function_response happens
        if not any(name == "calculate_profit" for name, _ in resps):
            return

        pa = state.get("profit_analysis") or {}
        if not isinstance(pa, dict) or not pa:
            return

        # Additional guard: don’t print the same profit_analysis twice
        fingerprint = json.dumps(pa, sort_keys=True, default=str)
        if fingerprint == self.last_profit_analysis_fingerprint:
            return
        self.last_profit_analysis_fingerprint = fingerprint

        status = "GREENLIGHT" if pa.get("is_profitable") else "REDESIGN REQUIRED"

        print(hr("AGENT D: PROFIT ANALYSIS"))
        print(" Calculating profitability...")

        print("\n" + box("AGENT D: PROFIT ANALYSIS COMPLETE"))
        print(f" {status}")
        print(" COST BREAKDOWN:")
        print(f"   Fabric Cost:  {money(pa.get('fabric_cost'))}")
        print(f"   Labor Cost:   {money(pa.get('labor_cost'))}")
        print(f"   Total Cost:   {money(pa.get('total_cost'))}")
        print(" REVENUE:")
        print(f"   Selling Price:{money(pa.get('selling_price'))}")
        print(" PROFITABILITY:")
        print(f"   Profit:       {money(pa.get('profit'))}")
        print(f"   Margin:       {pct(pa.get('profit_margin_percent'))}")
        print(f"   Target:       {pct(pa.get('target_margin_percent'))}")
        print(f" State updated: needs_optimization={state.get('needs_optimization')}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to garment image (jpg/png/webp).")
    ap.add_argument(
        "--prompt",
        default="Analyze the garment in the image and save garment specs (fabric, yardage, complexity).",
    )
    ap.add_argument("--session-id", default="session_structured", help="Session id.")
    ap.add_argument("--max-iterations", type=int, default=3, help="Should match LoopAgent max_iterations.")
    ap.add_argument("--target-margin", type=float, default=0.40, help="For display only.")
    args = ap.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    # Key count (display only)
    keys_env = os.getenv("GOOGLE_API_KEYS", "").strip()
    if keys_env:
        key_count = len([k for k in keys_env.split(",") if k.strip()])
    else:
        key_count = 1 if os.getenv("GOOGLE_API_KEY") else 0

    from src.executor import root_agent

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=args.session_id)

    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    printer = PipelinePrinter(
        image_name=image_path.name,
        target_margin=args.target_margin,
        max_iterations=args.max_iterations,
        key_count=key_count,
    )
    printer.print_banner()

    print("\n===== RUN: root_agent (full pipeline) =====")

    # Initial header for Agent A
    print(hr("AGENT A: GARMENT DECONSTRUCTION"))
    print(f" Analyzing: {image_path.name}")
    print(" Sending to vision model...")

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=args.session_id,
        new_message=make_image_message(image_path, args.prompt),
    ):
        agent = _get_agent_name(event)
        calls, resps, texts = _parse_event_parts(event)

        # Always print tool calls/results/text for this event
        print_event_io(agent, calls, resps, texts)

        # Pull state and print structured “complete” cards (gated to avoid repeats)
        session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=args.session_id)
        state = _extract_state(session)

        printer.maybe_print_agent_a_complete(state, resps)
        printer.maybe_print_agent_b_complete(state)
        printer.maybe_print_agent_c_complete(state)
        printer.maybe_print_agent_d_complete(state, resps)

    # Final focused result (kept)
    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=args.session_id)
    state = _extract_state(session)
    print("\n" + hr("FINAL PIPELINE RESULT"))
    print(json.dumps({k: _jsonable(v) for k, v in state.items()}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
