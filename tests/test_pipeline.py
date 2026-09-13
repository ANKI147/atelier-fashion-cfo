import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import run
from src.executor import build_root_agent, optimization_loop, root_agent
from src.planner import agent_optimizer
from src.tools import calculate_profit


class ProfitCalculationTests(unittest.TestCase):
    def make_context(self, target_margin=0.40):
        return SimpleNamespace(state={
            "fabric_cost": {"price_per_yard": 10, "yards_needed": 3},
            "market_price": {"average_price": 100},
            "garment_specs": {
                "garment_type": "dress",
                "construction_complexity": "Medium",
                "estimated_yardage": 3,
            },
            "target_profit_margin": target_margin,
        })

    def test_custom_target_changes_decision_without_changing_costs(self):
        lower = calculate_profit(self.make_context(0.40), labor_cost=20)
        higher = calculate_profit(self.make_context(0.60), labor_cost=20)
        self.assertTrue(lower["is_profitable"])
        self.assertFalse(higher["is_profitable"])
        self.assertEqual(lower["total_cost"], higher["total_cost"])
        self.assertEqual(higher["target_margin_percent"], 60)

    def test_exact_target_is_accepted_and_result_is_saved(self):
        context = self.make_context(0.50)
        result = calculate_profit(context, labor_cost=20)
        self.assertTrue(result["is_profitable"])
        self.assertEqual(result["profit_margin_percent"], 50)
        self.assertEqual(context.state["profit_analysis"], result)

    def test_default_target_and_json_agent_outputs(self):
        context = self.make_context()
        context.state.pop("target_profit_margin")
        for key in ("fabric_cost", "market_price"):
            context.state[key] = json.dumps(context.state[key])
        result = calculate_profit(context, labor_cost=20)
        self.assertEqual(result["target_margin_percent"], 40)
        self.assertEqual(result["profit"], 50)

    def test_labor_estimate_uses_garment_specs(self):
        result = calculate_profit(self.make_context())
        self.assertEqual(result["labor_cost"], 60)
        self.assertEqual(result["profit_margin_percent"], 10)
        self.assertFalse(result["is_profitable"])

    def test_missing_or_invalid_prices_cannot_greenlight(self):
        for key, field in (("fabric_cost", "price_per_yard"),
                           ("fabric_cost", "yards_needed"),
                           ("market_price", "average_price")):
            for value in (0, -1, float("nan"), float("inf")):
                with self.subTest(key=key, field=field, value=value):
                    context = self.make_context()
                    context.state[key][field] = value
                    with self.assertRaises(ValueError):
                        calculate_profit(context, labor_cost=20)

        context = self.make_context()
        context.state["fabric_cost"] = "not JSON"
        with self.assertRaises(ValueError):
            calculate_profit(context, labor_cost=20)

    def test_invalid_margin_and_labor_are_rejected(self):
        for target in (0, 1, -0.1, float("nan"), float("inf")):
            with self.subTest(target=target), self.assertRaises(ValueError):
                calculate_profit(self.make_context(target), labor_cost=20)
        for labor in (-1, float("nan"), float("inf")):
            with self.subTest(labor=labor), self.assertRaises(ValueError):
                calculate_profit(self.make_context(), labor_cost=labor)


class AgentConfigurationTests(unittest.TestCase):
    def test_loop_settings_are_isolated_between_runs(self):
        first = build_root_agent(1)
        second = build_root_agent(5)
        self.assertEqual(first.sub_agents[1].max_iterations, 1)
        self.assertEqual(second.sub_agents[1].max_iterations, 5)
        self.assertEqual(optimization_loop.max_iterations, 3)
        self.assertIsNot(first, root_agent)
        self.assertIsNot(first.sub_agents[0], second.sub_agents[0])
        self.assertIsNot(first.sub_agents[1].sub_agents[0], second.sub_agents[1].sub_agents[0])

    def test_invalid_loop_counts_are_rejected(self):
        for count in (0, -1, 1.5, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                build_root_agent(count)

    def test_optimizer_uses_tool_result_not_unresolved_template_expressions(self):
        self.assertIn("IF is_profitable is true", agent_optimizer.instruction)
        self.assertNotIn("{", agent_optimizer.instruction)
        self.assertNotIn("MARGIN TOO HIGH", agent_optimizer.instruction)


class EntryPointTests(unittest.TestCase):
    def test_cli_applies_custom_settings_without_calling_external_apis(self):
        captured = {}

        class OfflineRunner:
            def __init__(self, *, agent, app_name, session_service):
                captured["iterations"] = agent.sub_agents[1].max_iterations
                self.app_name = app_name
                self.session_service = session_service

            async def run_async(self, *, user_id, session_id, new_message):
                session = await self.session_service.get_session(
                    app_name=self.app_name, user_id=user_id, session_id=session_id
                )
                captured["margin"] = session.state["target_profit_margin"]
                yield SimpleNamespace(content=None)

        arguments = [
            "run.py", "--image", "sample.png",
            "--target-margin", "0.55", "--max-iterations", "2",
        ]
        with (
            patch("sys.argv", arguments),
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only", "SERPAPI_API_KEY": "test-only"}),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "read_bytes", return_value=b"sample-image"),
            patch.object(run, "Runner", OfflineRunner),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            asyncio.run(run.main())

        self.assertEqual(captured, {"iterations": 2, "margin": 0.55})

    def test_cli_rejects_invalid_settings_before_analysis(self):
        for option, value in (
            ("--max-iterations", "0"),
            ("--target-margin", "1"),
            ("--target-margin", "nan"),
        ):
            with (
                self.subTest(option=option, value=value),
                patch("sys.argv", ["run.py", "--image", "sample.png", option, value]),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as failure,
            ):
                asyncio.run(run.main())
            self.assertEqual(failure.exception.code, 2)

    def test_web_view_can_render_a_loss_and_custom_settings(self):
        from streamlit.testing.v1 import AppTest

        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app_test = AppTest.from_file(str(app_path), default_timeout=30).run()
        self.assertEqual(len(app_test.exception), 0)
        markdown = [element.value for element in app_test.markdown]
        self.assertEqual(markdown.count("Built by Ankit More"), 1)
        self.assertFalse(any("Built with" in value or "Hackathon Project" in value for value in markdown))
        self.assertFalse(any("Gemini API:" in value or "SerpAPI:" in value for value in markdown))
        self.assertFalse(any("Configuration" in heading.value for heading in app_test.header))
        app_test.slider[0].set_value(55)
        app_test.slider[1].set_value(2)
        app_test.session_state["final_state"] = {"profit_analysis": {
            "profit_margin_percent": -50,
            "target_margin_percent": 55,
            "is_profitable": False,
            "total_cost": 150,
            "profit": -50,
        }}
        app_test.run()
        self.assertEqual(len(app_test.exception), 0)
        self.assertEqual(app_test.slider[0].value, 55)
        self.assertEqual(app_test.slider[1].value, 2)
        self.assertTrue(any("NEEDS OPTIMIZATION" in warning.value for warning in app_test.warning))


if __name__ == "__main__":
    unittest.main()