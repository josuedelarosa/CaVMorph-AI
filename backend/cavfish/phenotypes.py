# backend/cavfish/phenotypes.py
from __future__ import annotations

from typing import List, Optional, Sequence, Dict, Any
import numpy as np


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def compute_phenotypes(
    keypoints_xy: np.ndarray,
    pairs: Sequence[Sequence[int]],
    scale_by_sl: bool,
    sl_pair: Optional[Sequence[int]],
) -> List[Dict[str, Any]]:
    """
    Returns a list of phenotype measurements derived from keypoint pairs.
    - value_px: Euclidean distance in pixels
    - value_norm: distance normalized by SL (if enabled)
    """
    phenos: List[Dict[str, Any]] = []

    sl_value = None
    if scale_by_sl:
        if sl_pair is None or len(sl_pair) != 2:
            # If training assumed scale_by_SL but we don't know SL here, we still output px
            sl_value = None
        else:
            i, j = int(sl_pair[0]), int(sl_pair[1])
            sl_value = _dist(keypoints_xy[i], keypoints_xy[j])
            if sl_value <= 1e-6:
                sl_value = None

    for idx, p in enumerate(pairs):
        i, j = int(p[0]), int(p[1])
        dpx = _dist(keypoints_xy[i], keypoints_xy[j])
        dnorm = (dpx / sl_value) if (sl_value is not None) else None
        phenos.append({
            "id": idx,
            "pair": [i, j],
            "name": f"pair_{i}_{j}",
            "value_px": dpx,
            "value_norm": dnorm,
        })

    return phenos

