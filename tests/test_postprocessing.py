"""
Fishometrics Test Suite — Postprocessing Tests

Validates heatmap decoding and keypoint transformation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from inference_runtime.postprocessing import (
    decode_udp_heatmaps,
    transform_keypoints_to_original,
    compute_phenotypes,
)


def _make_gaussian_heatmap(
    hm_w: int, hm_h: int, cx: float, cy: float, sigma: float = 2.0
) -> np.ndarray:
    """Create a 2D Gaussian heatmap centered at (cx, cy)."""
    y = np.arange(hm_h, dtype=np.float32)
    x = np.arange(hm_w, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    hm = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))
    return hm


class TestDecodeUDPHeatmaps:
    def test_single_point_at_center(self):
        """A Gaussian at the heatmap center should decode near the input image center."""
        hm_w, hm_h = 48, 64
        inp_w, inp_h = 192, 256

        hm = _make_gaussian_heatmap(hm_w, hm_h, hm_w / 2, hm_h / 2, sigma=2.0)
        heatmaps = hm[np.newaxis]  # (1, 64, 48)

        kps, scores = decode_udp_heatmaps(heatmaps, (inp_w, inp_h), (hm_w, hm_h))
        assert kps.shape == (1, 2)
        assert scores.shape == (1,)

        # Should be near center of input image
        assert kps[0, 0] == pytest.approx(inp_w / 2, abs=4.0)
        assert kps[0, 1] == pytest.approx(inp_h / 2, abs=4.0)
        assert scores[0] > 0.9

    def test_multiple_keypoints(self):
        """Multiple heatmap channels should produce multiple keypoints."""
        hm_w, hm_h = 48, 64
        inp_w, inp_h = 192, 256

        heatmaps = np.stack([
            _make_gaussian_heatmap(hm_w, hm_h, 10, 10),
            _make_gaussian_heatmap(hm_w, hm_h, 40, 50),
        ])  # (2, 64, 48)

        kps, scores = decode_udp_heatmaps(heatmaps, (inp_w, inp_h), (hm_w, hm_h))
        assert kps.shape == (2, 2)

        # First keypoint near top-left
        assert kps[0, 0] < inp_w / 2
        assert kps[0, 1] < inp_h / 2

        # Second keypoint near bottom-right
        assert kps[1, 0] > inp_w / 2
        assert kps[1, 1] > inp_h / 2

    def test_scores_reflect_confidence(self):
        """A strong peak should have a higher score than a weak peak."""
        hm_w, hm_h = 48, 64

        strong = _make_gaussian_heatmap(hm_w, hm_h, 24, 32, sigma=2.0)
        weak = _make_gaussian_heatmap(hm_w, hm_h, 24, 32, sigma=2.0) * 0.3
        heatmaps = np.stack([strong, weak])

        _, scores = decode_udp_heatmaps(heatmaps, (192, 256), (hm_w, hm_h))
        assert scores[0] > scores[1]


class TestTransformKeypoints:
    def test_center_maps_to_center(self):
        """Center of input image should map near center of a centered original image."""
        center = np.array([320.0, 240.0], dtype=np.float32)
        scale = np.array([800.0, 600.0], dtype=np.float32)
        input_size = (192, 256)

        # A keypoint at the center of the input image
        kps = np.array([[96.0, 128.0]], dtype=np.float32)
        original = transform_keypoints_to_original(kps, center, scale, input_size)

        assert original.shape == (1, 2)
        assert original[0, 0] == pytest.approx(320.0, abs=5.0)
        assert original[0, 1] == pytest.approx(240.0, abs=5.0)

    def test_roundtrip(self):
        """Preprocessing then postprocessing should recover original coords."""
        from inference_runtime.preprocessing import preprocess_image, get_inverse_warp_matrix

        img = np.zeros((480, 640, 3), dtype=np.uint8)
        _, center, scale = preprocess_image(
            img, (192, 256),
            np.array([123.675, 116.28, 103.53]),
            np.array([58.395, 57.12, 57.375]),
        )

        # Put a keypoint at the input image center.
        # Under UDP, this does not necessarily map to exact original image center.
        kps = np.array([[96.0, 128.0]], dtype=np.float32)
        original = transform_keypoints_to_original(kps, center, scale, (192, 256))

        # Validate against direct inverse affine mapping from preprocessing.
        inv = get_inverse_warp_matrix(center, scale, (192, 256))
        kph = np.array([kps[0, 0], kps[0, 1], 1.0], dtype=np.float32)
        expected = inv @ kph

        assert original[0, 0] == pytest.approx(float(expected[0]), abs=1e-4)
        assert original[0, 1] == pytest.approx(float(expected[1]), abs=1e-4)


class TestComputePhenotypes:
    def test_euclidean_distance(self):
        kps = np.array([
            [0.0, 0.0],
            [3.0, 4.0],
        ], dtype=np.float32)
        result = compute_phenotypes(
            kps, pairs=[[0, 1]], scale_by_sl=False, sl_pair=None
        )
        assert len(result) == 1
        assert result[0]["value_px"] == pytest.approx(5.0)
        assert result[0]["value_norm"] is None

    def test_x_distance(self):
        kps = np.array([[10.0, 20.0], [30.0, 50.0]], dtype=np.float32)
        result = compute_phenotypes(
            kps, pairs=[[0, 1]], scale_by_sl=False, sl_pair=None,
            phenotype_types=["x"],
        )
        assert result[0]["value_px"] == pytest.approx(20.0)

    def test_y_distance(self):
        kps = np.array([[10.0, 20.0], [30.0, 50.0]], dtype=np.float32)
        result = compute_phenotypes(
            kps, pairs=[[0, 1]], scale_by_sl=False, sl_pair=None,
            phenotype_types=["y"],
        )
        assert result[0]["value_px"] == pytest.approx(30.0)

    def test_sl_normalization(self):
        kps = np.array([
            [0.0, 0.0],
            [100.0, 0.0],
            [0.0, 50.0],
        ], dtype=np.float32)
        result = compute_phenotypes(
            kps,
            pairs=[[0, 2]],
            scale_by_sl=True,
            sl_pair=[0, 1],  # SL = 100px
        )
        assert result[0]["value_px"] == pytest.approx(50.0)
        assert result[0]["value_norm"] == pytest.approx(0.5)

    def test_phenotype_names(self):
        kps = np.array([[0, 0], [1, 0]], dtype=np.float32)
        result = compute_phenotypes(
            kps, pairs=[[0, 1]], scale_by_sl=False, sl_pair=None,
            phenotype_names=["BodyLength"],
        )
        assert result[0]["name"] == "BodyLength"
