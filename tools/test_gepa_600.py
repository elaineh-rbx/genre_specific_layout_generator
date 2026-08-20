from __future__ import annotations

import pathlib
import tempfile
import math

from PIL import Image

from layoutgen.optimize.gepa_600 import (
    WeakestContractStageSelector,
    frame_errors,
    golden_validation_scenes,
    optimization_context,
    robust_objective,
    select_training_scenes,
)
from layoutgen.optimize.gepa_images import SceneCase


def _case(scene: str, order: str = "std") -> SceneCase:
    return SceneCase(scene, order, "iso", "first", "addendum", {}, "author")


def test_select_training_scenes_is_exact_and_deterministic() -> None:
    cases = {f"P{index:04d}": _case(f"P{index:04d}") for index in range(1, 617)}
    first, excluded = select_training_scenes(cases, 600, 19)
    second, _ = select_training_scenes(cases, 600, 19)
    assert first == second
    assert len(first) == 600
    assert len(excluded) == 16
    assert not set(first) & set(excluded)


def test_golden_validation_requires_all_75() -> None:
    cases = {f"{index:04d}": _case(f"{index:04d}") for index in range(1, 76)}
    cases["P0002"] = _case("P0002")
    assert golden_validation_scenes(cases) == [
        f"{index:04d}" for index in range(1, 76)
    ]


def test_robust_objective_penalizes_lower_tail() -> None:
    scores = [1.0] * 8 + [0.0] * 2
    assert math.isclose(robust_objective(scores), 0.64)


def test_no_recaption_context_contains_no_recaption_instructions() -> None:
    objective, background = optimization_context(False)
    assert "recaption" not in objective.lower()
    assert "recaption" not in background.lower()
    enabled_objective, enabled_background = optimization_context(True)
    assert "recaption" in enabled_objective.lower()
    assert "recaption" in enabled_background.lower()


def test_frame_errors_detects_black_letterbox() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "image.png"
        image = Image.new("RGB", (100, 100), "white")
        for y in list(range(6)) + list(range(94, 100)):
            for x in range(100):
                image.putpixel((x, y), (0, 0, 0))
        image.save(path)
        errors = frame_errors(path)
    assert "solid black top letterbox/border band" in errors
    assert "solid black bottom letterbox/border band" in errors


def test_stage_selector_uses_final_objective_for_active_stage() -> None:
    selector = WeakestContractStageSelector()
    trajectories = [
        {"Render order": "std", "scores": {"combined_objective": 0.9}},
        {"Render order": "p6", "scores": {"combined_objective": 0.2}},
    ]
    selected = selector(
        None,
        trajectories,
        [0.9, 0.2],
        0,
        {"iso": "i", "topdown": "t", "plan": "p"},
    )
    assert selected == ["plan"]


if __name__ == "__main__":
    tests = [
        test_select_training_scenes_is_exact_and_deterministic,
        test_golden_validation_requires_all_75,
        test_robust_objective_penalizes_lower_tail,
        test_no_recaption_context_contains_no_recaption_instructions,
        test_frame_errors_detects_black_letterbox,
        test_stage_selector_uses_final_objective_for_active_stage,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
