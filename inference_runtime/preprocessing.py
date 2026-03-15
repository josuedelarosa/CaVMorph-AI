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
    # Match MMPose UDP warp matrix (pixel-center aligned):
    # scale_x = (dst_w - 1) / src_w, scale_y = (dst_h - 1) / src_h
    # then apply rotation + translation in closed form.
    src_w = float(scale[0])
    src_h = float(scale[1])
    dst_w, dst_h = int(output_size[0]), int(output_size[1])

    rot_rad = float(np.deg2rad(rot))
    cos_r = float(np.cos(rot_rad))
    sin_r = float(np.sin(rot_rad))

    scale_x = (dst_w - 1.0) / src_w
    scale_y = (dst_h - 1.0) / src_h

    tx = scale_x * (
        -0.5 * src_w * cos_r + 0.5 * src_h * sin_r + float(center[0])
    )
    ty = scale_y * (
        -0.5 * src_w * sin_r - 0.5 * src_h * cos_r + float(center[1])
    )

    warp_mat = np.array(
        [
            [scale_x * cos_r, -scale_x * sin_r, tx],
            [scale_y * sin_r, scale_y * cos_r, ty],
        ],
        dtype=np.float32,
    )
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


def _fix_aspect_ratio(scale: np.ndarray, aspect_ratio: float) -> np.ndarray:
    """Match MMPose TopdownAffine bbox aspect-ratio correction.

    Args:
        scale: [w, h] bbox scale in pixels.
        aspect_ratio: target w/h ratio (e.g. 192/256).

    Returns:
        Corrected [w, h] scale that matches target aspect ratio.
    """
    w, h = float(scale[0]), float(scale[1])
    if w > h * aspect_ratio:
        h = w / aspect_ratio
    elif w < h * aspect_ratio:
        w = h * aspect_ratio
    return np.array([w, h], dtype=np.float32)


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

    # TopdownAffine fixes bbox scale to the model input aspect ratio before warping.
    scale = _fix_aspect_ratio(scale, aspect_ratio=float(out_w) / float(out_h))

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
