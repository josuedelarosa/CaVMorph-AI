# Inference Runtime — Preprocessing
"""
Pure NumPy/OpenCV preprocessing pipeline that replicates the MMPose inference
transforms without any MMPose dependency:

  1. Full-image bounding box
  2. GetBBoxCenterScale(padding=1.25)
  3. TopdownAffine(input_size=(W,H), use_udp=True)
  4. PoseDataPreprocessor normalization (ImageNet mean/std, BGR→RGB)

This must produce identical tensor values to the MMPose pipeline to maintain
numerical parity with the legacy system.
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def get_warp_matrix_udp(
    center: np.ndarray,
    scale: np.ndarray,
    rot: float,
    output_size: Tuple[int, int],
) -> np.ndarray:
    """Get the affine transformation matrix for UDP (Unbiased Data Processing).

    This replicates mmpose's `top_down_affine` with `use_udp=True`.

    Args:
        center: Center of the bounding box (x, y).
        scale: Scale of the bounding box (w, h) in pixels.
        rot: Rotation in degrees.
        output_size: (W, H) of the output image.

    Returns:
        2x3 affine transformation matrix.
    """
    src_w = scale[0]
    src_h = scale[1]
    dst_w, dst_h = output_size

    rot_rad = np.deg2rad(rot)
    cos_r = np.cos(rot_rad)
    sin_r = np.sin(rot_rad)

    # Source points (UDP-style: pixel centers)
    src_dir = np.array([0, src_w * -0.5], dtype=np.float32)
    src_dir_rot = np.array(
        [src_dir[0] * cos_r - src_dir[1] * sin_r,
         src_dir[0] * sin_r + src_dir[1] * cos_r],
        dtype=np.float32,
    )

    src = np.zeros((3, 2), dtype=np.float32)
    src[0] = center
    src[1] = center + src_dir_rot
    # Third point is perpendicular
    src[2] = src[1] + np.array([-src_dir_rot[1], src_dir_rot[0]])

    dst = np.zeros((3, 2), dtype=np.float32)
    dst[0] = np.array([dst_w * 0.5, dst_h * 0.5], dtype=np.float32)
    dst[1] = np.array([dst_w * 0.5, dst_h * 0.5 - dst_w * 0.5], dtype=np.float32)
    dst[2] = dst[1] + np.array([dst_w * 0.5, 0], dtype=np.float32)  # perpendicular

    # UDP pixel alignment: shift by -0.5 then +0.5 to align to pixel grid
    dst[0] += -0.5
    dst[1] += -0.5
    dst[2] += -0.5

    warp_mat = cv2.getAffineTransform(src.astype(np.float32), dst.astype(np.float32))
    return warp_mat


def _bbox_xyxy_to_center_scale(
    bbox: np.ndarray, padding: float = 1.25
) -> Tuple[np.ndarray, np.ndarray]:
    """Convert [x1, y1, x2, y2] bbox to center + scale with padding.

    Replicates GetBBoxCenterScale transform behavior.
    """
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    center = np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5], dtype=np.float32)
    scale = np.array([w, h], dtype=np.float32) * padding
    return center, scale


def preprocess_image(
    image_bgr: np.ndarray,
    input_size: Tuple[int, int],
    mean: np.ndarray,
    std: np.ndarray,
    padding: float = 1.25,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full preprocessing pipeline: BGR image → normalized CHW float32 tensor.

    Replicates the exact MMPose inference preprocessing chain:
      1. Full-image bbox
      2. GetBBoxCenterScale(padding)
      3. TopdownAffine(input_size, use_udp=True)
      4. PoseDataPreprocessor(mean, std, bgr_to_rgb=True)

    Args:
        image_bgr: Input BGR uint8 image (H, W, 3).
        input_size: Model input (W, H) — e.g., (192, 256).
        mean: Normalization mean [R, G, B] (ImageNet default).
        std: Normalization std [R, G, B].
        padding: BBox padding factor.

    Returns:
        tensor: Preprocessed (1, 3, H, W) float32 array.
        center: BBox center (2,).
        scale: BBox scale (2,).
    """
    h, w = image_bgr.shape[:2]
    bbox = np.array([0.0, 0.0, float(w), float(h)], dtype=np.float32)
    center, scale = _bbox_xyxy_to_center_scale(bbox, padding)

    out_w, out_h = input_size  # (192, 256)

    # TopdownAffine with UDP
    warp_mat = get_warp_matrix_udp(center, scale, rot=0.0, output_size=(out_w, out_h))
    warped = cv2.warpAffine(
        image_bgr,
        warp_mat,
        (out_w, out_h),
        flags=cv2.INTER_LINEAR,
    )

    # BGR → RGB (matching PoseDataPreprocessor bgr_to_rgb=True)
    rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)

    # Normalize: (pixel - mean) / std
    img_float = rgb.astype(np.float32)
    mean_arr = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std_arr = np.array(std, dtype=np.float32).reshape(1, 1, 3)
    normalized = (img_float - mean_arr) / std_arr

    # HWC → CHW and add batch dim
    tensor = normalized.transpose(2, 0, 1)  # (3, H, W)
    tensor = np.expand_dims(tensor, 0)  # (1, 3, H, W)

    return tensor, center, scale


def get_inverse_warp_matrix(
    center: np.ndarray,
    scale: np.ndarray,
    output_size: Tuple[int, int],
) -> np.ndarray:
    """Get the inverse affine transform to map from heatmap coords back to original image.

    Used in postprocessing to convert keypoint coordinates.
    """
    warp_mat = get_warp_matrix_udp(center, scale, rot=0.0, output_size=output_size)
    # Invert the 2x3 affine matrix
    inv_mat = cv2.invertAffineTransform(warp_mat)
    return inv_mat
