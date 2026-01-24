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
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    keypoint_names = meta.get("keypoint_names", [f"kp{i+1}" for i in range(20)])
    phenotype_pairs = meta.get("phenotype_pairs", [])

    fieldnames = ["image_path"]

    # Add keypoint columns
    for i, name in enumerate(keypoint_names):
        fieldnames.extend([f"{name}_x", f"{name}_y", f"{name}_conf"])

    # Add phenotype columns
    for i, pair in enumerate(phenotype_pairs):
        i_kp, j_kp = pair
        pair_name = f"pair_{i_kp}_{j_kp}"
        fieldnames.extend([f"{pair_name}_px", f"{pair_name}_norm"])

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pred in predictions:
            row = {"image_path": pred.get("image_path", "")}

            # Extract keypoints
            kpts = pred.get("keypoints", [])
            scores = pred.get("keypoint_scores", [])

            for i, name in enumerate(keypoint_names):
                if i < len(kpts):
                    kpt = kpts[i]
                    if isinstance(kpt, (list, tuple)) and len(kpt) >= 2:
                        row[f"{name}_x"] = kpt[0]
                        row[f"{name}_y"] = kpt[1]
                    else:
                        row[f"{name}_x"] = ""
                        row[f"{name}_y"] = ""
                else:
                    row[f"{name}_x"] = ""
                    row[f"{name}_y"] = ""

                if i < len(scores):
                    row[f"{name}_conf"] = scores[i]
                else:
                    row[f"{name}_conf"] = ""

            # Extract phenotypes (if available in pred)
            extra_fields = pred.get("extra_pred_fields", {})
            phenotypes_data = extra_fields.get("phenotypes", [])

            for idx, pair in enumerate(phenotype_pairs):
                pair_name = f"pair_{pair[0]}_{pair[1]}"
                if idx < len(phenotypes_data):
                    pheno = phenotypes_data[idx]
                    row[f"{pair_name}_px"] = pheno.get("value_px", "")
                    row[f"{pair_name}_norm"] = pheno.get("value_norm", "")
                else:
                    row[f"{pair_name}_px"] = ""
                    row[f"{pair_name}_norm"] = ""

            writer.writerow(row)


def export_json(path: str, predictions: Sequence[Dict[str, Any]]) -> None:
    """Export predictions to JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(predictions), f, indent=2)


def export_annotated_images(
    output_dir: str,
    predictions: Sequence[Dict[str, Any]],
    suffix: str = "_annotated",
) -> None:
    """
    Export annotated images (with keypoints drawn).
    Reads overlay_path from each prediction and copies/links them.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for pred in predictions:
        overlay_path = pred.get("overlay_path")
        if overlay_path is None:
            continue

        overlay_file = Path(overlay_path)
        if not overlay_file.exists():
            continue

        image_path = pred.get("image_path", "")
        if image_path:
            stem = Path(image_path).stem
            out_name = f"{stem}{suffix}.png"
        else:
            out_name = overlay_file.name

        out_file = output_path / out_name
        cv2.imwrite(str(out_file), cv2.imread(str(overlay_file)))
