"""Tests for model-specific image-prompt adaptation."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from layoutgen.pipeline import prompts
from layoutgen.pipeline import spec as pipeline_spec


class PromptProfileTests(unittest.TestCase):
    def test_default_profile_does_not_change_prompt(self) -> None:
        env = {
            "LAYOUTGEN_IMAGE_BACKEND": "azure",
            "LAYOUTGEN_IMAGE_MODEL": "",
            "LAYOUTGEN_IMAGE_PROMPT_PROFILE": "",
        }
        with mock.patch.dict(os.environ, env):
            self.assertEqual(prompts.profile_name(), "default")
            self.assertEqual(prompts.for_model("unchanged", "iso"), "unchanged")

    def test_gateway_gemini_gets_quality_and_camera_rules(self) -> None:
        env = {
            "LAYOUTGEN_IMAGE_BACKEND": "llm-gateway",
            "LAYOUTGEN_IMAGE_MODEL": "gemini-3.1-flash-image",
            "LAYOUTGEN_IMAGE_PROMPT_PROFILE": "",
        }
        request = {
            "source": "Build a bank and gas station with visible entrances.",
            "genre": "",
            "mode": "std",
        }
        with mock.patch.dict(os.environ, env):
            built = pipeline_spec.build(request)

        self.assertEqual(built["prompt_profile"], "gemini")
        for prompt in (built["iso"], built["topdown"]):
            self.assertTrue(prompt.startswith("Create one polished, richly detailed"))
            self.assertIn("do not simplify", prompt)
            self.assertIn("bank and gas station", prompt)
            self.assertIn("Roblox-like", prompt)
            self.assertIn("Physical arrows", prompt)
        self.assertIn("50-to-60 degrees away from vertical nadir", built["iso"])
        self.assertIn("exactly 90-degree straight-down", built["topdown"])
        self.assertGreater(
            built["iso"].find("FINAL CAMERA REQUIREMENT"),
            built["iso"].find("bank and gas station"),
        )
        self.assertGreater(
            built["topdown"].find("FINAL CAMERA REQUIREMENT"),
            built["topdown"].find("bank and gas station"),
        )

    def test_gateway_default_model_selects_gemini_profile(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "LAYOUTGEN_IMAGE_BACKEND": "llm-gateway",
                "LAYOUTGEN_IMAGE_PROMPT_PROFILE": "",
            },
            clear=True,
        ):
            self.assertEqual(prompts.profile_name(), "gemini")

    def test_plan_profile_avoids_diagram_style_wording(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"LAYOUTGEN_IMAGE_PROMPT_PROFILE": "gemini"},
        ):
            built = pipeline_spec.build(
                {"source": "Build a 12-stage obstacle course.", "mode": "p6"}
            )

        self.assertEqual(built["prompt_profile"], "gemini")
        self.assertIn("an exactly 90-degree straight-down", built["plan"])
        self.assertIn("overhead nadir plan of the layout", built["plan"])
        self.assertTrue(
            built["plan"].endswith(
                "zero perspective, zero horizon, zero side faces, and zero visible "
                "wall height."
            )
        )

    def test_gemini_v2_uses_stage_specific_contract_and_checklist(self) -> None:
        request = {
            "source": "Build a mountain road with three roadside plateaus.",
            "genre": "Simulation",
            "shape": "world-open",
            "options": ["path-road-vehicle"],
            "edits": {
                "path-road-vehicle": (
                    "One continuous switchback road with exactly three plateaus."
                )
            },
            "mode": "p6",
        }
        with mock.patch.dict(
            os.environ,
            {"LAYOUTGEN_IMAGE_PROMPT_PROFILE": "gemini-v2"},
        ):
            built = pipeline_spec.build(request)

        self.assertEqual(built["prompt_profile"], "gemini-v2")
        self.assertTrue(built["plan"].startswith("TEXT-TO-IMAGE OVERHEAD"))
        self.assertTrue(built["iso"].startswith("IMAGE-EDIT TASK"))
        self.assertNotIn("Create one polished, richly detailed", built["plan"])
        for prompt in (built["plan"], built["iso"]):
            self.assertIn("FINAL MUST-SHOW CHECKLIST", prompt)
            self.assertIn(
                "One continuous switchback road with exactly three plateaus.",
                prompt,
            )
        self.assertIn("30-to-35 degrees away from vertical nadir", built["iso"])
        self.assertIn(
            "Connectivity and exact counts must be unambiguous", built["plan"]
        )

    def test_unknown_profile_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown image prompt profile"):
            prompts.for_model("prompt", "iso", "mystery")

    def test_gepa_profile_keeps_canonical_prompt_and_loads_stage_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = pathlib.Path(temporary) / "candidate.json"
            candidate.write_text(
                json.dumps(
                    {
                        "iso": "OPTIMIZED ISO POLICY",
                        "topdown": "OPTIMIZED TOPDOWN POLICY",
                        "plan": "OPTIMIZED PLAN POLICY",
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {
                    "LAYOUTGEN_IMAGE_PROMPT_PROFILE": "gemini-gepa",
                    "LAYOUTGEN_GEPA_CANDIDATE": str(candidate),
                },
            ):
                adapted = prompts.for_model(
                    "EXACT CANONICAL SCENE CONTRACT", "iso"
                )

        self.assertIn("EXACT CANONICAL SCENE CONTRACT", adapted)
        self.assertIn("OPTIMIZED ISO POLICY", adapted)
        self.assertIn("may not remove, replace, merge", adapted)


if __name__ == "__main__":
    unittest.main()
