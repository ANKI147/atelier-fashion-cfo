import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# If your .env is inside src/, prefer this:
# load_dotenv(Path(__file__).resolve().parent / "src" / ".env")
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

print("GOOGLE_API_KEY present:", bool(os.getenv("GOOGLE_API_KEY")))

from src.planner import agent_analyzer, agent_sourcer, agent_market  # [file:189]

APP_NAME = "Atelier"
USER_ID = "local_user"
SESSION_ID = "session_ABC"


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


def make_text_message(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part.from_text(text=text)])


def _extract_state(session):
    # ADK session objects differ by version; try common patterns.
    if hasattr(session, "state") and isinstance(session.state, dict):
        return session.state
    if hasattr(session, "context") and isinstance(session.context, dict):
        return session.context
    return None


def print_state_snapshot(session) -> None:
    state = _extract_state(session)
    if not isinstance(state, dict):
        print("\n[STATE] Could not find dict-like state on Session.")
        print(session)
        return

    keys = [
        # Agent outputs (output_key) [file:189]
        "garment_info",
        "fabric_cost",
        "market_price",
        # Tool-written structured state (recommended for downstream) [file:189]
        "garment_specs",
        "fabric_pricing",
        "market_data",
        "suggested_alternative",
    ]
    snapshot = {k: state.get(k) for k in keys if k in state}

    print("\n[STATE] Snapshot:")
    print(json.dumps(snapshot, indent=2, default=str))


async def run_agent(label: str, agent, runner: Runner, msg: types.Content):
    print(f"\n===== RUN: {label} =====")
    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=msg):
        if getattr(event, "content", None) and getattr(event.content, "parts", None):
            for part in event.content.parts:
                # Print streamed text; tool calls may show as non-text parts.
                if getattr(part, "text", None):
                    print(part.text)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to garment image (jpg/png/webp).")
    ap.add_argument(
        "--prompt",
        default="Analyze the garment in the image and save garment specs (fabric, yardage, complexity).",
        help="Prompt for Agent A.",
    )
    ap.add_argument(
        "--skip-search",
        action="store_true",
        help="Run only Agent A (useful if google_search quotas/keys aren't set yet).",
    )
    args = ap.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    # Create separate runners but share the SAME session_service + session_id => shared state across A/B/C. [file:189]
    runner_a = Runner(agent=agent_analyzer, app_name=APP_NAME, session_service=session_service)
    runner_b = Runner(agent=agent_sourcer, app_name=APP_NAME, session_service=session_service)
    runner_c = Runner(agent=agent_market, app_name=APP_NAME, session_service=session_service)

    # A: image -> garment_specs + garment_info [file:189]
    await run_agent("Agent A (image_analyzer)", agent_analyzer, runner_a, make_image_message(image_path, args.prompt))

    if not args.skip_search:
        # B: fabric sourcing (uses google_search + save_fabric_cost) [file:189]
        await run_agent("Agent B (sourcer)", agent_sourcer, runner_b, make_text_message("Find wholesale fabric cost now."))

        # C: market research (uses google_search + save_market_price) [file:189]
        await run_agent("Agent C (market_researcher)", agent_market, runner_c, make_text_message("Find market price now."))

    session = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    print_state_snapshot(session)


if __name__ == "__main__":
    asyncio.run(main())
