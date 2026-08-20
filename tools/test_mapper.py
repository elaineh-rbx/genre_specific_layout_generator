"""Regression checks for procedural layout dispatch."""

from __future__ import annotations

import unittest

from layoutgen.model import blob, rules as br
from layoutgen.pipeline import mapper


def _spec(genre: str, shape: str, first: str) -> dict:
    return {
        "initial_scene_subprompt_enriched": "Scene-specific enriched geometry.",
        "genre": genre,
        "shape": shape,
        "axes": {},
        "options": [],
        "render": {"first": first},
    }


class MapperProceduralDispatchTest(unittest.TestCase):
    def _option_spec(
        self,
        option_id: str,
        *,
        genre: str = "Action",
        visible: bool = True,
        route: list[str] | None = None,
        placed: bool = False,
    ) -> dict:
        spec = _spec(genre, "space-bounded", "isometric")
        spec.update({
            "preset": "none",
            "layout_placement": ([{
                "id": option_id,
                "text": f"Scene-specific {option_id}.",
                "count": 1,
                "where": "At the selected gameplay location.",
            }] if placed else []),
            "route": route or ["P0"],
            "notes": [],
        })
        spec["options"] = [{
            "id": option_id,
            "text": f"Scene-specific {option_id}.",
            "visible": visible,
            "count": 1,
        }]
        return blob.normalise(spec)

    def test_enriched_prompt_is_required(self) -> None:
        spec = _spec("Action", "arena-tiered", "isometric")
        spec["initial_scene_subprompt_enriched"] = ""

        with self.assertRaisesRegex(ValueError, "initial_scene_subprompt_enriched"):
            mapper.build(spec)

    def test_final_scoped_body_reaches_both_views_for_every_order(self) -> None:
        cases = (
            ("Action", "space-bounded", "isometric"),
            ("Action", "space-bounded", "topdown"),
            ("Racing", "route-circuit", "authored_plan"),
        )
        scoped = "ONLY THE SELECTED ACTIVE HARBOUR."
        for genre, shape, first in cases:
            with self.subTest(first=first):
                spec = _spec(genre, shape, first)
                spec["initial_scene_subprompt_enriched"] = scoped
                built = mapper.build(spec)
                second = (
                    built["topdown"]
                    if built["order"] in {"std", "layout"}
                    else built["plan"]
                )
                self.assertIn(scoped, built["iso"])
                self.assertIn(scoped, second)

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
                    self.assertIn("Two scene-specific protected starts.", prompt)
                    self.assertNotIn(
                        "Start areas set back, screened by walls or terrain",
                        prompt,
                    )

    def test_cross_genre_option_keeps_contextual_requirement(self) -> None:
        spec = _spec("Sports", "space-bounded", "isometric")
        spec.update({
            "preset": "none",
            "layout_placement": [],
            "route": ["P0"],
            "notes": [],
        })
        spec["options"] = [{
            "id": "alcove-secret",
            "text": "A recessed equipment alcove beneath the home-team stands.",
            "visible": True,
            "count": 1,
        }]

        spec = blob.normalise(spec)
        built = mapper.build(spec)

        self.assertEqual([o["id"] for o in spec["options"]], ["alcove-secret"])
        self.assertIn(
            "A recessed equipment alcove beneath the home-team stands.",
            built["iso"],
        )
        self.assertNotIn(
            "Hidden cutouts behind waterfalls, fake walls, or overgrowth",
            built["iso"],
        )

    def test_cross_genre_variable_routes_follow_the_explicit_decision(self) -> None:
        cases = [
            ("path-road-vehicle", "Sports", ["P0"], "P6", False),
            ("path-road-vehicle", "Sports", ["P6"], "P6", True),
            ("teleporter-link", "Sports", ["P4"], "P4", True),
            ("teleporter-link", "Sports", ["P0"], "P4", False),
            ("spectator-zone", "Puzzle", ["P0", "tiered"], "tiered", True),
        ]
        for option_id, genre, claimed, modifier, expected in cases:
            with self.subTest(option_id=option_id, claimed=claimed):
                spec = self._option_spec(
                    option_id,
                    genre=genre,
                    route=claimed,
                    placed=option_id == "teleporter-link",
                )
                built = mapper.build(spec)
                self.assertEqual(modifier in built["route"], expected)

    def test_cross_genre_variable_destinations_keep_the_explicit_split(self) -> None:
        cases = (
            ("checkpoint-respawn", "Action"),
            ("collectible-nodes", "Action"),
            ("spawn-protected", "Adventure"),
            ("trigger-scoring", "Action"),
        )
        for option_id, genre in cases:
            with self.subTest(option_id=option_id):
                spec = self._option_spec(
                    option_id, genre=genre, visible=True, placed=True
                )
                pick = spec["options"][0]
                self.assertTrue(pick["visible"])
                self.assertEqual(spec["layout_placement"][0]["id"], option_id)

                built = mapper.build(spec)
                self.assertIn(f"Scene-specific {option_id}.", built["iso"])
                self.assertEqual(built["placements"][0]["id"], option_id)

    def test_cross_genre_variable_layout_pick_is_mirrored_and_withheld(self) -> None:
        spec = self._option_spec("trigger-scoring", visible=False)

        self.assertFalse(spec["options"][0]["visible"])
        self.assertEqual(spec["layout_placement"][0]["id"], "trigger-scoring")
        built = mapper.build(spec)
        self.assertNotIn("Scene-specific trigger-scoring.", built["iso"])
        self.assertTrue(any("layout (explicit)" in row for row in built["withheld"]))

    def test_no_genre_options_are_in_the_shared_runtime_catalogue(self) -> None:
        self.assertEqual(len(br.OPTION_CATALOG), 93)
        for option_id in ("boundary-edge", "spawn-area"):
            with self.subTest(option_id=option_id):
                self.assertIsNotNone(br.GENRES["Action"].option(option_id))

    def test_normalise_does_not_duplicate_persistent_repair_notes(self) -> None:
        spec = self._option_spec("trigger-scoring", visible=False, placed=True)
        spec["layout_placement"][0]["where"] = ""

        blob.normalise(spec)
        blob.normalise(spec)

        message = "placement 'trigger-scoring' carries no siting rule"
        self.assertEqual(spec["notes"].count(message), 1)

    def test_unsupported_authored_plan_falls_back_to_image_plan(self) -> None:
        built = mapper.build(_spec("RPG", "world-open", "authored_plan"))

        self.assertEqual(built["order"], "p6")
        self.assertEqual(built["first"], "topdown")
        self.assertIsNone(built["kind"])


if __name__ == "__main__":
    unittest.main()
