from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import build_agent_arm

artifact = build_agent_arm.artifact
final_scoped_prompt = build_agent_arm.final_scoped_prompt


class AgentArtifactTest(unittest.TestCase):
    def test_decision_only_artifact(self) -> None:
        self.assertEqual(
            artifact("# Agent decision\n\n## Clarifications resolved\nNone."),
            "## Clarifications resolved\nNone.",
        )

    def test_legacy_intermediate_section_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must begin"):
            artifact(
                "# Scene " + "prompt\nLegacy intermediate.\n\n"
                "# Agent decision\n\n## Clarifications resolved\nNone."
            )

    def test_empty_decision_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            artifact("# Agent decision")

    def test_extracts_only_the_final_scoped_image_prompt(self) -> None:
        prose = (
            "## Scope reduction result\n"
            "Active: the harbour.\n\n"
            "## Final scoped image prompt\n"
            "Build only the compact harbour.\n\n"
            "## Audit note\n"
            "Not part of the image prompt."
        )

        self.assertEqual(
            final_scoped_prompt(prose), "Build only the compact harbour."
        )

    def test_final_scoped_image_prompt_is_required_once(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            final_scoped_prompt("## Genre\nRPG.")

    def test_instruction_version_includes_scope_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = pathlib.Path(tmp) / "SKILL.md"
            scope.write_text("first scope policy", encoding="utf-8")
            with mock.patch.object(build_agent_arm, "SCOPE_SKILL", scope):
                first = build_agent_arm.version()

            scope.write_text("second scope policy", encoding="utf-8")
            with mock.patch.object(build_agent_arm, "SCOPE_SKILL", scope):
                second = build_agent_arm.version()

        self.assertNotEqual(first, second)

    def test_process_reads_source_from_supplied_input_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            prose = root / "P0001.md"
            prose.write_text(
                "# Agent decision\n\n## Genre\nStrategy.", encoding="utf-8"
            )
            inputs = root / "inputs"
            inputs.mkdir()
            (inputs / "P0001.json").write_text(
                json.dumps(
                    {
                        "source": "Build a small strategy map.",
                        "answers": [{"answer": "Use a compact scale."}],
                    }
                ),
                encoding="utf-8",
            )
            built = {"scene": "P0001"}
            with mock.patch.object(
                build_agent_arm, "build_one", return_value=built
            ) as build_one:
                scene, status, result, detail = build_agent_arm.process(
                    prose, input_dir=inputs
                )

        self.assertEqual((scene, status, result, detail), ("P0001", "ok", built, ""))
        build_one.assert_called_once_with(
            "P0001",
            "# Agent decision\n\n## Genre\nStrategy.",
            "Build a small strategy map.",
            [{"answer": "Use a compact scale."}],
        )

    def test_build_one_does_not_normalise_an_exact_genre_twice(self) -> None:
        spec = {"genre": "RPG", "secondary": []}
        built = {"order": "std", "first": "isometric", "notes": []}
        with (
            mock.patch.object(build_agent_arm.blob, "decouple", return_value=spec),
            mock.patch.object(build_agent_arm.blob, "normalise") as normalise,
            mock.patch.object(build_agent_arm.mapper, "build", return_value=built),
            mock.patch.object(build_agent_arm.llm, "schema_degraded", return_value=False),
            mock.patch.object(build_agent_arm.llm, "served_by", return_value="test"),
            mock.patch.object(build_agent_arm, "version", return_value="test-version"),
        ):
            build_agent_arm.build_one(
                "0001",
                "# Agent decision\n\n## Genre\nRPG.\n\n"
                "## Final scoped image prompt\nScoped arena.",
                "source",
                [],
            )

        normalise.assert_not_called()
        self.assertEqual(
            spec["initial_scene_subprompt_enriched"], "Scoped arena."
        )

    def test_build_one_renormalises_after_genre_canonicalisation(self) -> None:
        raw = {"genre": "rpg", "secondary": []}
        canonical = {"genre": "RPG", "secondary": []}
        built = {"order": "std", "first": "isometric", "notes": []}
        with (
            mock.patch.object(build_agent_arm.blob, "decouple", return_value=raw),
            mock.patch.object(
                build_agent_arm.blob, "normalise", return_value=canonical
            ) as normalise,
            mock.patch.object(build_agent_arm.mapper, "build", return_value=built),
            mock.patch.object(build_agent_arm.llm, "schema_degraded", return_value=False),
            mock.patch.object(build_agent_arm.llm, "served_by", return_value="test"),
            mock.patch.object(build_agent_arm, "version", return_value="test-version"),
        ):
            result = build_agent_arm.build_one(
                "0001",
                "# Agent decision\n\n## Genre\nRPG.\n\n"
                "## Final scoped image prompt\nScoped arena.",
                "source",
                [],
            )

        normalise.assert_called_once()
        self.assertEqual(result["spec"]["genre"], "RPG")
        self.assertEqual(
            result["spec"]["initial_scene_subprompt_enriched"], "Scoped arena."
        )
        self.assertEqual(result["prompt_boundary"], "final_scoped_image_prompt")


if __name__ == "__main__":
    unittest.main()
