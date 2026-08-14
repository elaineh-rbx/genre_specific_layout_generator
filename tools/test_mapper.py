"""Regression checks for procedural layout dispatch."""

from __future__ import annotations

import unittest

from layoutgen.pipeline import mapper


def _spec(genre: str, shape: str, first: str) -> dict:
    return {
        "scene_prompt": "Original scene prompt.",
        "initial_scene_subprompt_enriched": "Scene-specific enriched geometry.",
        "genre": genre,
        "shape": shape,
        "axes": {},
        "options": [],
        "render": {"first": first},
    }


class MapperProceduralDispatchTest(unittest.TestCase):
    def test_supported_track_forces_track_generator(self) -> None:
        built = mapper.build(_spec("Racing", "route-circuit", "topdown"))

        self.assertEqual(built["order"], "layout")
        self.assertEqual(built["first"], "authored_plan")
        self.assertEqual(built["kind"], "track")
        self.assertIn("LAYOUT FEATURES", built["addendum"])
        self.assertIn(built["addendum"], built["iso"])
        self.assertIn("Scene-specific enriched geometry.", built["iso"])
        self.assertEqual(built["prompt_source"], "agent_enriched_plus_catalogue")
        self.assertTrue(any("track generator available" in note for note in built["notes"]))

    def test_supported_maze_forces_maze_generator(self) -> None:
        built = mapper.build(_spec("Puzzle", "puzzle-maze", "isometric"))

        self.assertEqual(built["order"], "layout")
        self.assertEqual(built["first"], "authored_plan")
        self.assertEqual(built["kind"], "maze")
        self.assertIn("LAYOUT FEATURES", built["addendum"])

    def test_enriched_prompt_keeps_visible_option_requirement(self) -> None:
        for first in ("isometric", "topdown"):
            with self.subTest(first=first):
                spec = _spec("Action", "arena-tiered", first)
                spec["options"] = [{
                    "id": "spawn-protected",
                    "text": "Two scene-specific protected starts.",
                    "visible": True,
                    "count": 2,
                }]

                built = mapper.build(spec)
                td_prompt = (
                    built["plan"] if built["order"] == "p6" else built["topdown"]
                )

                for prompt in (built["iso"], td_prompt):
                    self.assertIn("Scene-specific enriched geometry.", prompt)
                    self.assertIn(
                        "Start areas set back, screened by walls or terrain",
                        prompt,
                    )

    def test_unsupported_authored_plan_falls_back_to_image_plan(self) -> None:
        built = mapper.build(_spec("RPG", "world-open", "authored_plan"))

        self.assertEqual(built["order"], "p6")
        self.assertEqual(built["first"], "topdown")
        self.assertIsNone(built["kind"])


if __name__ == "__main__":
    unittest.main()
