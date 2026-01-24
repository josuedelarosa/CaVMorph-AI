# backend/cavfish/infer.py
from __future__ import annotations

from typing import Any, Dict, List
import os
import torch
import numpy as np
from mmpose.apis import inference_topdown
from mmpose.structures import merge_data_samples

from .phenotypes import compute_phenotypes


def infer_image(model: Any, meta: Dict[str, Any], image_path: str) -> Dict[str, Any]:
    image_path = os.path.abspath(image_path)

    with torch.no_grad():
        dev = next(model.parameters()).device
        if dev.type == "cuda":
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                batch_results = inference_topdown(model, image_path)
        else:
            batch_results = inference_topdown(model, image_path)

    results = merge_data_samples(batch_results)

    # First instance (single fish assumption)
    kps = results.pred_instances.keypoints[0]         # (K,2)
    scs = results.pred_instances.keypoint_scores[0]   # (K,)

    keypoint_names: List[str] = meta["keypoint_names"]
    K = int(meta["num_keypoints"])
    if len(kps) != K:
        raise RuntimeError(f"Model returned {len(kps)} keypoints, expected {K}")

    keypoints = []
    for i in range(K):
        keypoints.append({
            "id": i,
            "name": keypoint_names[i],
            "x": float(kps[i][0]),
            "y": float(kps[i][1]),
            "score": float(scs[i]),
        })

    phenos = compute_phenotypes(
        keypoints_xy=np.asarray(kps, dtype=np.float32),
        pairs=meta.get("phenotype_pairs", []),
        scale_by_sl=bool(meta.get("phenotype_scale_by_sl", False)),
        sl_pair=meta.get("phenotype_sl_pair", None),
    )

    return {
        "image_path": image_path,
        "image_name": os.path.basename(image_path),
        "num_keypoints": K,
        "keypoints": keypoints,
        "phenotypes": phenos,
    }

