from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools import build_pipeline_viewer as viewer


class ScopeComparisonTest(unittest.TestCase):
    def test_extracts_one_prose_section(self) -> None:
        text = (
            "# Agent decision\n"
            "## Enriched image prompt\nActive zone only.\n\n"
            "## Genre\nRPG.\n"
        )
        self.assertEqual(
            viewer.prose_section(text, "Enriched image prompt"),
            "Active zone only.",
        )

    def test_loads_manifest_failure_without_promoting_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            prose = root / "prose"
            prose.mkdir()
            images = root / "images"
            (images / "iso").mkdir(parents=True)
            (images / "td").mkdir()
            (images / "iso" / "P0001.png").touch()
            (images / "td" / "P0001.png").touch()
            (prose / "P0001.md").write_text(
                "# Agent decision\n"
                "## Genre\nRPG.\n"
                "## Shape and preset\nUse `space-bounded`.\n"
                "## Scale, theme, and pipeline cost\n"
                "Full route is `P4`.\n"
                "## Scope reduction result\n"
                "Active zone: one arena.\n"
                "## Final scoped image prompt\nOne arena.\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "run_name": "fresh-v2",
                        "instruction_version": "abc123",
                        "scene_count": 1,
                        "structurally_valid_outputs": 1,
                        "validation_failures": {"P0001": "wrong active zone"},
                    }
                ),
                encoding="utf-8",
            )

            rows = viewer.scope_comparisons(prose, manifest, images)

        self.assertEqual(rows["P0001"]["scope_after_enriched"], "One arena.")
        self.assertEqual(
            rows["P0001"]["scope_after_ledger"],
            "Active zone: one arena.",
        )
        self.assertEqual(rows["P0001"]["scope_after_genre"], "RPG.")
        self.assertEqual(
            rows["P0001"]["scope_after_shape"], "Use `space-bounded`."
        )
        self.assertTrue(rows["P0001"]["scope_after_fired"])
        self.assertEqual(
            rows["P0001"]["scope_after_failure"], "wrong active zone"
        )
        self.assertEqual(rows["P0001"]["scope_after_run"], "fresh-v2")
        self.assertEqual(
            set(rows["P0001"]["scope_after_images"]),
            {"iso", "td"},
        )

    def test_comparison_markup_is_present(self) -> None:
        page = viewer.build_page([{"scope_after_blob": "fresh decision"}])
        self.assertIn('id="scopeCompare"', page)
        self.assertIn("Before / after", page)
        self.assertIn("known semantic failure", page)
        self.assertIn("scope-skill comparison", page)
        self.assertIn('id="sumReduced"', page)
        self.assertIn("Compare &amp; contrast this scene", page)
        self.assertIn('id="afterIsoImage"', page)
        self.assertIn("prompt-only isometric preview", page)
        self.assertIn('id="sumAfterRendered"', page)
        self.assertIn("const VIEWER_AFTER_IMAGE_COUNT = 0;", page)


if __name__ == "__main__":
    unittest.main()
