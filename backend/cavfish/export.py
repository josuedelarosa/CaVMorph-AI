# backend/cavfish/export.py
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import cv2
import numpy as np


def export_csv(
    path: str,
    predictions: Sequence[Dict[str, Any]],
    meta: Dict[str, Any],
) -> None:
    """
    Export predictions to CSV with columns:
    - image_path
    - keypoint_1_x, keypoint_1_y, keypoint_1_conf, ...
    - phenotype_pair_0_1_px, phenotype_pair_0_1_norm, ...
    
    NOTE: This function now respects the filtered keypoints in predictions.
    If predictions have been filtered, only those keypoints will be exported.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if len(predictions) == 0:
        return

    # Get the number of keypoints from the first prediction (after filtering)
    first_pred = predictions[0]
    kpts = first_pred.get("keypoints", [])
    
    # Check if keypoints are in dict format
    if isinstance(kpts, list) and len(kpts) > 0 and isinstance(kpts[0], dict):
        # Dict format - use names from dicts
        keypoint_names = [kpt.get("name", f"kp{i+1}") for i, kpt in enumerate(kpts)]
    else:
        # Array format - flatten if nested
        if isinstance(kpts, list) and len(kpts) > 0:
            if isinstance(kpts[0], list) and len(kpts[0]) > 0:
                if isinstance(kpts[0][0], list) and len(kpts[0][0]) == 2:
                    kpts = kpts[0] if len(kpts) == 1 else kpts
        
        num_keypoints = len(kpts)
        # Use generic keypoint names based on actual count
        keypoint_names = [f"kp{i+1}" for i in range(num_keypoints)]
    
    # Get phenotypes from first prediction (they're already filtered)
    phenotypes_data = first_pred.get("extra_pred_fields", {}).get("phenotypes", [])

    fieldnames = ["image_path"]

    # Add keypoint columns (only for keypoints that exist)
    for i, name in enumerate(keypoint_names):
        fieldnames.extend([f"{name}_x", f"{name}_y"])

    # Add phenotype columns (only for phenotypes that exist in filtered data)
    for pheno in phenotypes_data:
        pheno_name = pheno.get("name", f"pheno_{pheno.get('id', 0)}")
        fieldnames.append(f"{pheno_name}_px")

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pred in predictions:
            row = {"image_path": pred.get("image_path", "")}

            # Extract keypoints - handle multiple formats
            kpts = pred.get("keypoints", [])
            scores = pred.get("keypoint_scores", [])
            
            # Check if keypoints are in dict format: [{"x":..., "y":..., "score":..., "name":...}, ...]
            if isinstance(kpts, list) and len(kpts) > 0 and isinstance(kpts[0], dict):
                # Dict format - extract directly
                for i, name in enumerate(keypoint_names):
                    if i < len(kpts):
                        kpt = kpts[i]
                        row[f"{name}_x"] = kpt.get("x", "")
                        row[f"{name}_y"] = kpt.get("y", "")
                    else:
                        row[f"{name}_x"] = ""
                        row[f"{name}_y"] = ""
            else:
                # Array format - legacy handling
                # Flatten if nested: [[[x,y],...]] -> [[x,y],...]
                if isinstance(kpts, list) and len(kpts) > 0:
                    if isinstance(kpts[0], list) and len(kpts[0]) > 0:
                        # Check if it's [[x,y], ...] (correct) or [[[x,y], ...]] (nested)
                        if isinstance(kpts[0][0], list) and len(kpts[0][0]) == 2:
                            # It's [[[x,y], ...]], flatten to [[x,y], ...]
                            kpts = kpts[0] if len(kpts) == 1 else kpts

                for i, name in enumerate(keypoint_names):
                    x_val = ""
                    y_val = ""
                    
                    # Extract x, y from keypoint
                    if i < len(kpts):
                        kpt = kpts[i]
                        # Handle both [x, y] and [[x, y]] formats
                        if isinstance(kpt, (list, tuple)):
                            if len(kpt) >= 2:
                                # Could be [x, y] or [[x, y]]
                                if isinstance(kpt[0], (list, tuple)):
                                    # It's [[x, y]]
                                    x_val = float(kpt[0][0]) if len(kpt[0]) > 0 else ""
                                    y_val = float(kpt[0][1]) if len(kpt[0]) > 1 else ""
                                else:
                                    # It's [x, y]
                                    x_val = float(kpt[0])
                                    y_val = float(kpt[1])
                    
                    row[f"{name}_x"] = x_val
                    row[f"{name}_y"] = y_val

            # Extract phenotypes from this prediction (already filtered)
            extra_fields = pred.get("extra_pred_fields", {})
            pred_phenotypes = extra_fields.get("phenotypes", [])

            # Add phenotype values by name
            for pheno in pred_phenotypes:
                pheno_name = pheno.get("name", f"pheno_{pheno.get('id', 0)}")
                row[f"{pheno_name}_px"] = pheno.get("value_px", "")

            writer.writerow(row)


def _strip_value_norm(predictions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of predictions with value_norm stripped from phenotype objects."""
    result = []
    for pred in predictions:
        pred_copy = dict(pred)
        extra = pred_copy.get("extra_pred_fields")
        if extra:
            extra_copy = dict(extra)
            phenotypes = extra_copy.get("phenotypes")
            if phenotypes:
                extra_copy["phenotypes"] = [
                    {k: v for k, v in p.items() if k != "value_norm"}
                    for p in phenotypes
                ]
            pred_copy["extra_pred_fields"] = extra_copy
        result.append(pred_copy)
    return result


def export_json(path: str, predictions: Sequence[Dict[str, Any]]) -> None:
    """Export predictions to JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(_strip_value_norm(predictions), f, indent=2)


def export_annotated_images(
    output_dir: str,
    predictions: Sequence[Dict[str, Any]],
    suffix: str = "_annotated",
) -> None:
    """
    Export annotated images with keypoints drawn.
    Regenerates overlays with only the keypoints present in filtered predictions.
    """
    from cavfish.draw import draw_overlay
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for pred in predictions:
        image_path = pred.get("image_path", "")
        if not image_path:
            continue
        
        image_file = Path(image_path)
        if not image_file.exists():
            continue

        # Read the original image
        bgr = cv2.imread(str(image_file))
        if bgr is None:
            continue
        
        # Draw overlay with FILTERED keypoints (those in pred)
        # Since pred has been filtered by frontend, it only contains selected keypoints
        overlay_img = draw_overlay(bgr, pred)
        
        # Generate output filename
        stem = image_file.stem
        out_name = f"{stem}{suffix}.jpg"
        out_file = output_path / out_name
        
        # Save as JPEG with quality 95
        cv2.imwrite(str(out_file), overlay_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

