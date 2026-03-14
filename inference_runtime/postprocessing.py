# Inference Runtime — Postprocessing
"""
Pure NumPy implementation of UDPHeatmap decoding that converts model output
heatmaps to keypoint coordinates in original image space.

Replicates mmpose's UDPHeatmap.decode() without any mmpose dependency.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np


def _get_heatmap_maximum(heatmaps: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Get maximum response location and value from heatmaps.

    Args:
        heatmaps: (K, H, W) heatmap array.

    Returns:
        locs: (K, 2) — (x, y) coordinates of the peak per keypoint.
        vals: (K,) — peak values.
    """
    K, H, W = heatmaps.shape
    flat = heatmaps.reshape(K, -1)
    max_idx = np.argmax(flat, axis=1)
    vals = np.max(flat, axis=1)

    y = max_idx // W
    x = max_idx % W
    locs = np.stack([x, y], axis=1).astype(np.float32)  # (K, 2)
    return locs, vals


def decode_udp_heatmaps(
    heatmaps: np.ndarray,
    input_size: Tuple[int, int],
    heatmap_size: Tuple[int, int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Decode UDP heatmaps to keypoint coordinates in input image space.

    Replicates mmpose UDPHeatmap.decode() logic:
      1. Find peak location in each heatmap channel
      2. Apply sub-pixel refinement (Taylor expansion for UDP)
      3. Transform from heatmap coordinates to input image coordinates

    Args:
        heatmaps: (K, H, W) probability maps from the model.
        input_size: (W, H) of the model input image — e.g., (192, 256).
        heatmap_size: (W, H) of the heatmap — e.g., (48, 64).

    Returns:
        keypoints: (K, 2) keypoint coordinates in input image space.
        scores: (K,) confidence scores.
    """
    K, hm_h, hm_w = heatmaps.shape

    # Step 1: Find peak
    locs, scores = _get_heatmap_maximum(heatmaps)  # locs: (K, 2), scores: (K,)

    # Step 2: Sub-pixel refinement via Taylor expansion (UDP style)
    for k in range(K):
        px, py = int(locs[k, 0]), int(locs[k, 1])
        if 1 <= px < hm_w - 1 and 1 <= py < hm_h - 1:
            # First derivatives
            dx = 0.5 * (heatmaps[k, py, px + 1] - heatmaps[k, py, px - 1])
            dy = 0.5 * (heatmaps[k, py + 1, px] - heatmaps[k, py - 1, px])
            # Second derivatives
            dxx = heatmaps[k, py, px + 1] - 2 * heatmaps[k, py, px] + heatmaps[k, py, px - 1]
            dyy = heatmaps[k, py + 1, px] - 2 * heatmaps[k, py, px] + heatmaps[k, py - 1, px]
            dxy = 0.25 * (
                heatmaps[k, py + 1, px + 1]
                - heatmaps[k, py + 1, px - 1]
                - heatmaps[k, py - 1, px + 1]
                + heatmaps[k, py - 1, px - 1]
            )

            # Hessian
            det = dxx * dyy - dxy * dxy
            if abs(det) > 1e-6:
                # Newton step: offset = -H^{-1} * grad
                offset_x = -(dyy * dx - dxy * dy) / det
                offset_y = -(dxx * dy - dxy * dx) / det

                # Clamp to ±0.5 (within one pixel)
                offset_x = np.clip(offset_x, -0.5, 0.5)
                offset_y = np.clip(offset_y, -0.5, 0.5)

                locs[k, 0] += offset_x
                locs[k, 1] += offset_y

    # Step 3: Transform from heatmap coords to input image coords (UDP formula)
    # UDP formula: x_img = (x_hm + 0.5) * stride - 0.5
    # where stride = input_size / heatmap_size
    inp_w, inp_h = input_size
    stride_x = inp_w / hm_w
    stride_y = inp_h / hm_h

    keypoints = np.zeros_like(locs)
    keypoints[:, 0] = (locs[:, 0] + 0.5) * stride_x - 0.5
    keypoints[:, 1] = (locs[:, 1] + 0.5) * stride_y - 0.5

    return keypoints, scores


def transform_keypoints_to_original(
    keypoints: np.ndarray,
    center: np.ndarray,
    scale: np.ndarray,
    input_size: Tuple[int, int],
) -> np.ndarray:
    """Transform keypoints from input image space back to original image space.

    Uses the inverse of the preprocessing affine transform.

    Args:
        keypoints: (K, 2) keypoints in input image coords.
        center: BBox center used during preprocessing.
        scale: BBox scale used during preprocessing.
        input_size: (W, H) model input size.

    Returns:
        (K, 2) keypoints in original image coordinates.
    """
    from .preprocessing import get_warp_matrix_udp

    out_w, out_h = input_size
    warp_mat = get_warp_matrix_udp(center, scale, rot=0.0, output_size=(out_w, out_h))
    inv_mat = cv2.invertAffineTransform(warp_mat)

    # Apply inverse transform: [x', y'] = inv_mat @ [x, y, 1]
    K = keypoints.shape[0]
    ones = np.ones((K, 1), dtype=np.float32)
    kp_homo = np.hstack([keypoints.astype(np.float32), ones])  # (K, 3)
    original = kp_homo @ inv_mat.T  # (K, 2)

    return original


def compute_phenotypes(
    keypoints_xy: np.ndarray,
    pairs: list,
    scale_by_sl: bool,
    sl_pair: Optional[list],
    phenotype_names: Optional[list] = None,
    phenotype_types: Optional[list] = None,
) -> list:
    """Compute phenotype measurements from keypoints.

    Reuses the exact logic from backend/cavfish/phenotypes.py.
    """

    def _dist(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b))

    def _dist_x(a: np.ndarray, b: np.ndarray) -> float:
        return float(abs(a[0] - b[0]))

    def _dist_y(a: np.ndarray, b: np.ndarray) -> float:
        return float(abs(a[1] - b[1]))

    sl_value = None
    if scale_by_sl and sl_pair and len(sl_pair) == 2:
        i, j = int(sl_pair[0]), int(sl_pair[1])
        sl_value = _dist(keypoints_xy[i], keypoints_xy[j])
        if sl_value <= 1e-6:
            sl_value = None

    phenos = []
    for idx, p in enumerate(pairs):
        i, j = int(p[0]), int(p[1])

        dist_type = "xy"
        if phenotype_types and idx < len(phenotype_types):
            dist_type = phenotype_types[idx].lower()

        if dist_type == "x":
            dpx = _dist_x(keypoints_xy[i], keypoints_xy[j])
        elif dist_type == "y":
            dpx = _dist_y(keypoints_xy[i], keypoints_xy[j])
        else:
            dpx = _dist(keypoints_xy[i], keypoints_xy[j])

        dnorm = (dpx / sl_value) if (sl_value is not None) else None

        if phenotype_names and idx < len(phenotype_names):
            name = phenotype_names[idx]
        else:
            name = f"pair_{i}_{j}"

        phenos.append({
            "id": idx,
            "pair": [i, j],
            "name": name,
            "type": dist_type,
            "value_px": dpx,
            "value_norm": dnorm,
        })

    return phenos
