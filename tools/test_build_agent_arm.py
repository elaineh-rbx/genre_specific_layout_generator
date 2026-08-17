from __future__ import annotations

import unittest
from unittest import mock

from tools import build_agent_arm

artifact = build_agent_arm.artifact


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
                "0001", "# Agent decision\n\n## Genre\nRPG.", "source", []
            )

        normalise.assert_not_called()

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
                "0001", "# Agent decision\n\n## Genre\nRPG.", "source", []
            )

        normalise.assert_called_once()
        self.assertEqual(result["spec"]["genre"], "RPG")


if __name__ == "__main__":
    unittest.main()
