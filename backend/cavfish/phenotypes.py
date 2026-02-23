# backend/cavfish/phenotypes.py
from __future__ import annotations

from typing import List, Optional, Sequence, Dict, Any
import numpy as np


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two points."""
    return float(np.linalg.norm(a - b))


def _dist_x(a: np.ndarray, b: np.ndarray) -> float:
    """Absolute distance along x-axis only."""
    return float(abs(a[0] - b[0]))


def _dist_y(a: np.ndarray, b: np.ndarray) -> float:
    """Absolute distance along y-axis only."""
    return float(abs(a[1] - b[1]))


def compute_phenotypes(
    keypoints_xy: np.ndarray,
    pairs: Sequence[Sequence[int]],
    scale_by_sl: bool,
    sl_pair: Optional[Sequence[int]],
    phenotype_names: Optional[List[str]] = None,
    phenotype_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns a list of phenotype measurements derived from keypoint pairs.
    
    Args:
        keypoints_xy: Nx2 array of keypoint coordinates
        pairs: List of keypoint index pairs to measure
        scale_by_sl: Whether to normalize by standard length
        sl_pair: Keypoint pair to use as standard length
        phenotype_names: Optional custom names for each phenotype
        phenotype_types: Optional distance types: 'x', 'y', or 'xy' (euclidean)
        
    Returns:
        List of phenotype measurements with:
        - value_px: Distance in pixels (according to specified type)
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
        
        # Determine distance calculation type
        dist_type = 'xy'  # default to euclidean
        if phenotype_types and idx < len(phenotype_types):
            dist_type = phenotype_types[idx].lower()
        
        # Calculate distance based on type
        if dist_type == 'x':
            dpx = _dist_x(keypoints_xy[i], keypoints_xy[j])
        elif dist_type == 'y':
            dpx = _dist_y(keypoints_xy[i], keypoints_xy[j])
        else:  # 'xy' or default
            dpx = _dist(keypoints_xy[i], keypoints_xy[j])
        
        dnorm = (dpx / sl_value) if (sl_value is not None) else None
        
        # Use custom name if provided, otherwise fallback to pair_i_j
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

