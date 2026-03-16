# backend/cavfish/draw.py
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple, Union

import cv2
import numpy as np


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _iter_keypoints_from_pred(pred: Dict[str, Any]) -> List[Tuple[float, float, float, str]]:
    """
    Return a list of (x, y, score, label) for drawing.

    Supports 2 common formats:
    1) Demo-style list of dicts:
       pred["keypoints"] = [{"name": "...", "x":..., "y":..., "score":...}, ...]
    2) MMPose-style arrays:
       pred["keypoints"] = [[[x,y], ...]]  (shape: [N=1][K][2])
       pred["keypoint_scores"] = [[s,...]] (shape: [N=1][K])
    """
    if not isinstance(pred, dict):
        return []

    kps = pred.get("keypoints", None)

    # --- Case 1: demo-style list of dicts ---
    if isinstance(kps, list) and len(kps) > 0 and isinstance(kps[0], dict):
        out: List[Tuple[float, float, float, str]] = []
        for i, kp in enumerate(kps):
            x = _as_float(kp.get("x", 0.0))
            y = _as_float(kp.get("y", 0.0))
            s = _as_float(kp.get("score", 1.0), default=1.0)
            name = str(kp.get("name", str(i)))
            out.append((x, y, s, name))
        return out

    # --- Case 2: MMPose-style arrays ---
    # keypoints: [ [ [x,y], ... ] ] or [ [x,y], ... ]
    if isinstance(kps, (list, tuple)) and len(kps) > 0:
        # unwrap batch dim if present
        if len(kps) > 0 and isinstance(kps[0], (list, tuple)) and len(kps[0]) > 0 and isinstance(kps[0][0], (list, tuple)):
            kps0 = kps[0]  # K x 2
        else:
            kps0 = kps  # maybe already K x 2

        scores = pred.get("keypoint_scores", None)
        if isinstance(scores, (list, tuple)) and len(scores) > 0 and isinstance(scores[0], (list, tuple)):
            scores0 = scores[0]
        elif isinstance(scores, (list, tuple)):
            scores0 = scores
        else:
            scores0 = None

        out = []
        for i, xy in enumerate(kps0):
            if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                continue
            x = _as_float(xy[0])
            y = _as_float(xy[1])
            s = _as_float(scores0[i], default=1.0) if scores0 is not None and i < len(scores0) else 1.0
            out.append((x, y, s, str(i + 1)))
        return out

    return []


def draw_overlay(
    bgr: np.ndarray,
    pred: Dict[str, Any],
    *,
    kpt_thr: float = 0.05,
    radius: int = 4,
    thickness: int = -1,
) -> np.ndarray:
    """
    Draw predicted keypoints on top of the image.
    - bgr: OpenCV BGR image
    - pred: prediction dict (demo-style or mmpose-style)
    """
    out = bgr.copy()

    pts = _iter_keypoints_from_pred(pred)
    if len(pts) > 0:
        max_s = max(s for (_, _, s, _) in pts)
        # if scores are tiny, use a tiny threshold
        if max_s <= 0.1 and kpt_thr >= 0.05:
            kpt_thr = 0.0
            
    h, w = out.shape[:2]
    
    # Scale keypoint radius based on image dimensions for consistent visual size
    # Use 0.7% of the smaller dimension as the radius (increased by 75%)
    base_dim = min(h, w)
    dynamic_radius = max(3, int(base_dim * 0.007))  # Min 3px, scales with image size
    
    for (x, y, s, label) in pts:
        if s < kpt_thr:
            continue
        if not np.isfinite(x) or not np.isfinite(y):
            continue

        xi, yi = int(round(x)), int(round(y))
        # allow points outside, but skip absurd ones
        if xi < -w or xi > 2 * w or yi < -h or yi > 2 * h:
            continue

        # Simple red color for all keypoints (BGR format)
        color = (0, 0, 255)  # BGR: pure red
        
        # Draw main keypoint circle (no outline, no shadow)
        cv2.circle(out, (xi, yi), dynamic_radius, color, thickness, cv2.LINE_AA)
        
        # Scale font size with image dimensions for consistent visual size
        font_scale = max(0.5, base_dim * 0.001)  # Scales with image size, min 0.5
        font_thickness = max(2, int(base_dim * 0.003))  # Scales with image size, min 2
        label_offset_y = int(dynamic_radius * 2.5)
        
        # Black outline for label
        cv2.putText(
            out,
            label,
            (xi - 5, yi - label_offset_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            font_thickness + 1,
            cv2.LINE_AA,
        )
        # White text
        cv2.putText(
            out,
            label,
            (xi - 5, yi - label_offset_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            font_thickness,
            cv2.LINE_AA,
        )

    return out
