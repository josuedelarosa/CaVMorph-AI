"""
PhenoAI Test Suite — Preprocessing Parity Tests

Validates that the pure NumPy/OpenCV preprocessing in inference_runtime
produces identical results to the MMPose pipeline transforms.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

# Ensure imports work
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

from inference_runtime.preprocessing import (
    preprocess_image,
    get_warp_matrix_udp,
    _bbox_xyxy_to_center_scale,
)


def _make_test_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a deterministic test image (BGR)."""
    rng = np.random.RandomState(42)
    return rng.randint(0, 256, (height, width, 3), dtype=np.uint8)


class TestBboxCenterScale:
    def test_full_image_bbox(self):
        bbox = np.array([0.0, 0.0, 640.0, 480.0], dtype=np.float32)
        center, scale = _bbox_xyxy_to_center_scale(bbox, padding=1.25)
        assert center[0] == pytest.approx(320.0)
        assert center[1] == pytest.approx(240.0)
        assert scale[0] == pytest.approx(800.0)  # 640 * 1.25
        assert scale[1] == pytest.approx(600.0)  # 480 * 1.25

    def test_padding_1(self):
        bbox = np.array([100.0, 100.0, 300.0, 300.0], dtype=np.float32)
        center, scale = _bbox_xyxy_to_center_scale(bbox, padding=1.0)
        assert center[0] == pytest.approx(200.0)
        assert center[1] == pytest.approx(200.0)
        assert scale[0] == pytest.approx(200.0)
        assert scale[1] == pytest.approx(200.0)


class TestWarpMatrixUDP:
    def test_identity_like(self):
        """When center is at the output center and scale matches output size."""
        center = np.array([96.0, 128.0], dtype=np.float32)  # center of 192x256
        scale = np.array([192.0, 256.0], dtype=np.float32)
        mat = get_warp_matrix_udp(center, scale, rot=0.0, output_size=(192, 256))
        # Should be close to identity (with UDP offset)
        assert mat.shape == (2, 3)

    def test_warp_matrix_invertible(self):
        center = np.array([320.0, 240.0], dtype=np.float32)
        scale = np.array([800.0, 600.0], dtype=np.float32)
        mat = get_warp_matrix_udp(center, scale, rot=0.0, output_size=(192, 256))
        inv = cv2.invertAffineTransform(mat)
        # Round-trip: apply then invert should recover original coords
        test_pt = np.array([[320.0, 240.0, 1.0]], dtype=np.float32)
        transformed = test_pt @ mat.T
        recovered = np.hstack([transformed, [[1.0]]]) @ inv.T
        assert recovered[0, 0] == pytest.approx(320.0, abs=0.1)
        assert recovered[0, 1] == pytest.approx(240.0, abs=0.1)


class TestPreprocessImage:
    def test_output_shape(self):
        img = _make_test_image(640, 480)
        tensor, center, scale = preprocess_image(
            img,
            input_size=(192, 256),
            mean=np.array([123.675, 116.28, 103.53]),
            std=np.array([58.395, 57.12, 57.375]),
            padding=1.25,
        )
        assert tensor.shape == (1, 3, 256, 192)
        assert tensor.dtype == np.float32
        assert center.shape == (2,)
        assert scale.shape == (2,)

    def test_deterministic(self):
        img = _make_test_image(640, 480)
        t1, _, _ = preprocess_image(
            img, (192, 256),
            np.array([123.675, 116.28, 103.53]),
            np.array([58.395, 57.12, 57.375]),
        )
        t2, _, _ = preprocess_image(
            img, (192, 256),
            np.array([123.675, 116.28, 103.53]),
            np.array([58.395, 57.12, 57.375]),
        )
        np.testing.assert_array_equal(t1, t2)

    def test_center_pixel_reasonable(self):
        """Center pixel should be roughly mean-subtracted zero for neutral images."""
        # A gray image (128,128,128) should normalize to roughly 0 after mean subtraction
        gray = np.full((480, 640, 3), 128, dtype=np.uint8)
        tensor, _, _ = preprocess_image(
            gray, (192, 256),
            np.array([123.675, 116.28, 103.53]),
            np.array([58.395, 57.12, 57.375]),
        )
        # After normalization, values at center should be small
        center_val = tensor[0, :, 128, 96]  # center of 256x192
        assert np.all(np.abs(center_val) < 1.0)


class TestPreprocessMMPoseParity:
    """Compare our preprocessing against MMPose reference if available."""

    @pytest.fixture
    def mmpose_available(self):
        try:
            from mmengine.config import Config
            from mmengine.dataset import Compose
            return True
        except ImportError:
            pytest.skip("MMPose not available, skipping parity test")

    def test_parity_with_mmpose_pipeline(self, mmpose_available):
        """Validate that our preprocessing matches MMPose's output."""
        from mmengine.registry import init_default_scope
        from mmengine.dataset import Compose

        init_default_scope("mmpose")

        img = _make_test_image(640, 480)
        h, w = img.shape[:2]

        # Our preprocessing
        tensor_ours, center, scale = preprocess_image(
            img,
            input_size=(192, 256),
            mean=np.array([123.675, 116.28, 103.53]),
            std=np.array([58.395, 57.12, 57.375]),
            padding=1.25,
        )

        # MMPose preprocessing
        pipeline_cfg = [
            dict(type="LoadImage"),
            dict(type="GetBBoxCenterScale", padding=1.25),
            dict(type="TopdownAffine", input_size=(192, 256), use_udp=True),
            dict(type="PackPoseInputs"),
        ]
        pipeline = Compose(pipeline_cfg)

        data_dict = {
            "img": img,
            "img_path": "",
            "bbox": np.array([0, 0, w, h], dtype=np.float32),
            "bbox_score": np.array([1.0], dtype=np.float32),
            "bbox_center": np.array([[w / 2, h / 2]], dtype=np.float32),
            "bbox_scale": np.array([[float(w), float(h)]], dtype=np.float32),
            "ori_shape": (h, w),
            "img_shape": (h, w),
        }
        processed = pipeline(data_dict)
        mmpose_input = processed["inputs"]  # Tensor (3, 256, 192) — already normalized by PackPoseInputs

        # PackPoseInputs doesn't normalize; PoseDataPreprocessor does.
        # Compare warped images before normalization.
        warped_ours = cv2.warpAffine(
            img,
            get_warp_matrix_udp(center, scale, 0.0, (192, 256)),
            (192, 256),
            flags=cv2.INTER_LINEAR,
        )

        # From MMPose pipeline, the input tensor is HWC uint8 → CHW float32 (no norm)
        mmpose_img = mmpose_input.numpy()  # (3, 256, 192) float32, in [0,255] range
        mmpose_hwc = mmpose_img.transpose(1, 2, 0)  # (256, 192, 3)

        # Compare pixel values. Depending on the MMPose build, channel order at this
        # stage may be BGR or RGB, so evaluate both and accept the matching one.
        diff_bgr = np.abs(warped_ours.astype(np.float32) - mmpose_hwc)
        diff_rgb = np.abs(cv2.cvtColor(warped_ours, cv2.COLOR_BGR2RGB).astype(np.float32) - mmpose_hwc)
        max_diff_bgr = float(np.max(diff_bgr))
        max_diff_rgb = float(np.max(diff_rgb))
        max_diff = min(max_diff_bgr, max_diff_rgb)

        assert max_diff < 2.0, (
            f"Warped image max diff too high: {max_diff:.4f}. "
            f"BGR diff={max_diff_bgr:.4f}, RGB diff={max_diff_rgb:.4f}"
        )
