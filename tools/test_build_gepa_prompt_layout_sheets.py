from __future__ import annotations

import pathlib
import tempfile

from PIL import Image

from build_gepa_prompt_layout_sheets import (
    _figure,
    _grid_image,
    _metrics,
    _page,
    _sheet,
)


def test_metrics_reads_objective_components() -> None:
    row = {
        "score": 0.7,
        "feedback": {
            "scores": {
                "prompt_adherence": 0.8,
                "layout_following": 0.6,
                "isometric_camera": 0.9,
                "perceptual_similarity": 0.5,
            }
        },
    }
    assert _metrics(row) == {
        "objective": 0.7,
        "prompt": 0.8,
        "layout": 0.6,
        "camera": 0.9,
        "image": 0.5,
    }


def test_sheet_contains_image_only_model_figures() -> None:
    figures = [
        _figure(
            "0001",
            "assets/model/0001.jpg",
            "<Model>",
            0.75,
        ),
        _figure(
            "0001",
            "assets/missing/0001.jpg",
            "Missing model",
            available=False,
        ),
    ]
    sheet = _sheet(
        "0001", "std", figures
    )
    assert "<script>" not in sheet
    assert "&lt;Model&gt;" in sheet
    assert "assets/model/0001.jpg" in sheet
    assert "Objective 0.750" in sheet
    assert "Not evaluated" in sheet
    assert "Full user prompt" not in sheet


def test_page_is_printable_and_filterable() -> None:
    page = _page(["<article>one</article>"], "example-run")
    assert "@media print" in page
    assert 'id="search"' in page
    assert "example-run" in page


def test_grid_image_exports_five_columns() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        source = root / "source.png"
        destination = root / "grid.jpg"
        Image.new("RGB", (64, 64), "green").save(source)
        entries = [
            (f"Model {index}", source if index < 4 else None, 0.5)
            for index in range(5)
        ]
        _grid_image(entries, destination)
        with Image.open(destination) as grid:
            assert grid.size == (2560, 570)


if __name__ == "__main__":
    tests = [
        test_metrics_reads_objective_components,
        test_sheet_contains_image_only_model_figures,
        test_page_is_printable_and_filterable,
        test_grid_image_exports_five_columns,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
