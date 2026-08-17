"""Perceptual similarity between a candidate render and a frozen target render."""

from __future__ import annotations

import pathlib
import threading
import warnings
from dataclasses import asdict, dataclass
from typing import Protocol

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


@dataclass(frozen=True)
class DinoFeatures:
    semantic: np.ndarray
    spatial: np.ndarray


@dataclass(frozen=True)
class SimilarityBreakdown:
    score: float
    semantic: float
    spatial: float
    structure: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


class FeatureEncoder(Protocol):
    def encode(self, path: pathlib.Path) -> DinoFeatures: ...


def _normalise(vector: np.ndarray, axis: int = -1) -> np.ndarray:
    denominator = np.linalg.norm(vector, axis=axis, keepdims=True)
    return vector / np.maximum(denominator, 1e-12)


class PyramidEncoder:
    """Torch-free multiscale colour, composition, and edge features."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int, int], DinoFeatures] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(path: pathlib.Path) -> tuple[str, int, int]:
        stat = path.stat()
        return str(path.resolve()), stat.st_size, stat.st_mtime_ns

    def encode(self, path: pathlib.Path) -> DinoFeatures:
        key = self._key(path)
        with self._lock:
            if cached := self._cache.get(key):
                return cached
            with Image.open(path) as opened:
                image = np.asarray(
                    opened.convert("RGB").resize(
                        (256, 256), Image.Resampling.LANCZOS
                    ),
                    dtype=np.float32,
                ) / 255.0

            low = np.asarray(
                Image.fromarray(np.uint8(image * 255)).resize(
                    (24, 24), Image.Resampling.LANCZOS
                ),
                dtype=np.float32,
            ).reshape(-1) / 255.0
            histograms = [
                np.histogram(image[..., channel], bins=16, range=(0, 1))[0]
                for channel in range(3)
            ]
            histogram = np.concatenate(histograms).astype(np.float32)
            histogram /= max(float(histogram.sum()), 1.0)
            semantic = _normalise(np.concatenate([low, histogram]))

            gray = image.mean(axis=2)
            grad_y, grad_x = np.gradient(gray)

            def patch_grid(values: np.ndarray) -> np.ndarray:
                return (
                    values.reshape(8, 32, 8, 32)
                    .transpose(0, 2, 1, 3)
                    .reshape(64, 32, 32)
                )

            gray_patches = patch_grid(gray)
            low_patches = gray_patches.reshape(64, 8, 4, 8, 4).mean(axis=(2, 4))
            low_patches -= low_patches.mean(axis=(1, 2), keepdims=True)
            edge_patches = patch_grid(np.hypot(grad_x, grad_y))
            edge_patches = edge_patches.reshape(64, 8, 4, 8, 4).mean(axis=(2, 4))
            rgb_means = (
                image.reshape(8, 32, 8, 32, 3)
                .mean(axis=(1, 3))
                .reshape(64, 3)
            )

            spatial = np.concatenate(
                [
                    low_patches.reshape(64, -1),
                    edge_patches.reshape(64, -1),
                    rgb_means,
                ],
                axis=1,
            )
            spatial = _normalise(spatial)
            features = DinoFeatures(semantic=semantic, spatial=spatial)
            self._cache[key] = features
            return features


class DinoEncoder:
    """Lazy DINOv2 encoder with a path-and-mtime feature cache."""

    def __init__(
        self,
        model: str = "facebook/dinov2-small",
        device: str = "auto",
    ) -> None:
        self.model_name = model
        self.device_name = device
        self._processor = None
        self._model = None
        self._device = None
        self._cache: dict[tuple[str, int, int], DinoFeatures] = {}
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModel

        selected = self.device_name
        if selected == "auto":
            selected = "cuda" if torch.cuda.is_available() else "cpu"
        self._device = torch.device(selected)
        self._processor = AutoImageProcessor.from_pretrained(self.model_name)
        self._model = AutoModel.from_pretrained(self.model_name).to(self._device)
        self._model.eval()

    @staticmethod
    def _key(path: pathlib.Path) -> tuple[str, int, int]:
        stat = path.stat()
        return str(path.resolve()), stat.st_size, stat.st_mtime_ns

    def encode(self, path: pathlib.Path) -> DinoFeatures:
        key = self._key(path)
        with self._lock:
            if cached := self._cache.get(key):
                return cached
            self._load()

            import torch
            import torch.nn.functional as functional

            assert self._processor is not None
            assert self._model is not None
            assert self._device is not None
            with Image.open(path) as opened:
                image = opened.convert("RGB")
            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {name: value.to(self._device) for name, value in inputs.items()}
            with torch.inference_mode():
                hidden = self._model(**inputs).last_hidden_state[0]
                hidden = functional.normalize(hidden.float(), dim=-1)
            features = DinoFeatures(
                semantic=hidden[0].cpu().numpy(),
                spatial=hidden[1:].cpu().numpy(),
            )
            self._cache[key] = features
            return features


class AutoEncoder:
    """Prefer DINOv2, but remain usable when the system PyTorch build is broken."""

    def __init__(
        self,
        model: str = "facebook/dinov2-small",
        device: str = "auto",
    ) -> None:
        self._primary = DinoEncoder(model=model, device=device)
        self._fallback = PyramidEncoder()
        self._selected: FeatureEncoder | None = None
        self._lock = threading.Lock()

    def encode(self, path: pathlib.Path) -> DinoFeatures:
        with self._lock:
            if self._selected is None:
                try:
                    features = self._primary.encode(path)
                    self._selected = self._primary
                    return features
                except (ImportError, OSError, RuntimeError) as exc:
                    warnings.warn(
                        "DINOv2 is unavailable; using the torch-free perceptual "
                        f"pyramid encoder instead ({type(exc).__name__}: {exc})",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self._selected = self._fallback
            selected = self._selected
        assert selected is not None
        return selected.encode(path)


class CompositeImageSimilarity:
    """DINO semantics and aligned patch structure plus grayscale SSIM.

    Pixel equality is not useful for independently sampled image models. DINO's global
    token measures scene-level likeness, aligned patch tokens retain camera/layout
    pressure, and grayscale SSIM adds a model-independent structural signal.
    """

    def __init__(
        self,
        encoder: FeatureEncoder | None = None,
        *,
        semantic_weight: float = 0.55,
        spatial_weight: float = 0.30,
        structure_weight: float = 0.15,
    ) -> None:
        total = semantic_weight + spatial_weight + structure_weight
        if not np.isclose(total, 1.0):
            raise ValueError(f"similarity weights must sum to 1, got {total}")
        self.encoder = encoder or AutoEncoder()
        self.weights = (semantic_weight, spatial_weight, structure_weight)

    @staticmethod
    def _bounded_cosine(a: np.ndarray, b: np.ndarray) -> float:
        raw = float(np.sum(a * b))
        return float(np.clip(raw, 0.0, 1.0))

    @staticmethod
    def _ssim(a_path: pathlib.Path, b_path: pathlib.Path) -> float:
        def gray(path: pathlib.Path) -> np.ndarray:
            with Image.open(path) as opened:
                resized = opened.convert("L").resize((256, 256), Image.Resampling.LANCZOS)
            return np.asarray(resized, dtype=np.float32) / 255.0

        a, b = gray(a_path), gray(b_path)
        mu_a = gaussian_filter(a, sigma=1.5)
        mu_b = gaussian_filter(b, sigma=1.5)
        sigma_a = gaussian_filter(a * a, sigma=1.5) - mu_a * mu_a
        sigma_b = gaussian_filter(b * b, sigma=1.5) - mu_b * mu_b
        sigma_ab = gaussian_filter(a * b, sigma=1.5) - mu_a * mu_b
        c1, c2 = 0.01**2, 0.03**2
        numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
        denominator = (mu_a * mu_a + mu_b * mu_b + c1) * (
            sigma_a + sigma_b + c2
        )
        raw = float(np.mean(numerator / np.maximum(denominator, 1e-12)))
        return float(np.clip(raw, 0.0, 1.0))

    def compare(
        self,
        candidate: pathlib.Path,
        target: pathlib.Path,
    ) -> SimilarityBreakdown:
        candidate_features = self.encoder.encode(candidate)
        target_features = self.encoder.encode(target)
        semantic = self._bounded_cosine(
            candidate_features.semantic, target_features.semantic
        )
        if candidate_features.spatial.shape != target_features.spatial.shape:
            raise ValueError(
                "DINO patch grids differ: "
                f"{candidate_features.spatial.shape} vs "
                f"{target_features.spatial.shape}"
            )
        patch_cosines = np.sum(
            candidate_features.spatial * target_features.spatial, axis=-1
        )
        candidate_norm = np.linalg.norm(candidate_features.spatial, axis=-1)
        target_norm = np.linalg.norm(target_features.spatial, axis=-1)
        both_empty = (candidate_norm < 1e-9) & (target_norm < 1e-9)
        patch_cosines[both_empty] = 1.0
        spatial = float(np.clip(patch_cosines.mean(), 0.0, 1.0))
        structure = self._ssim(candidate, target)
        score = (
            self.weights[0] * semantic
            + self.weights[1] * spatial
            + self.weights[2] * structure
        )
        return SimilarityBreakdown(
            score=float(score),
            semantic=semantic,
            spatial=spatial,
            structure=structure,
        )
