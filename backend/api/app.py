# backend/api/app.py
from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import cv2

from backend.cavfish.model_pack import ensure_model_pack, read_meta
from backend.cavfish.manager import ModelManager
from backend.cavfish.infer import infer_image  # array-based infer_image(model, rgb, *, cfg_path=..., device=...)
from backend.cavfish.io import iter_images
from backend.cavfish.draw import draw_overlay
from backend.cavfish.phenotypes import compute_phenotypes
from backend.cavfish.export import export_csv, export_json, export_annotated_images

# --------------------------------------------------
# Path bootstrap
# --------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

logger = logging.getLogger("cavfish.api")
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------
# Config
# --------------------------------------------------
MODEL_DIR = Path(os.environ.get("FISH_MODEL_DIR", "models/cavfish_v1")).resolve()
DEVICE = os.environ.get("FISH_DEVICE", "cpu")

pack = ensure_model_pack(MODEL_DIR)

manager = ModelManager(
    str(pack.config_path),
    str(pack.weights_path),
    device=DEVICE,
)

app = FastAPI()

# Add CORS middleware to allow requests from Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (safe for localhost dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Safe meta loader (server must not crash if meta is empty/bad)
# --------------------------------------------------
def safe_read_meta(meta_path: Path) -> Dict[str, Any]:
    try:
        if meta_path is None:
            logger.warning("Meta path is None; using empty meta.")
            return {}
        if not meta_path.exists():
            logger.warning("Meta file does not exist at %s; using empty meta.", meta_path)
            return {}
        raw = meta_path.read_text(encoding="utf-8")
        if raw.strip() == "":
            logger.warning("Meta file is empty at %s; using empty meta.", meta_path)
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            try:
                return read_meta(meta_path)
            except Exception as e:
                logger.exception(
                    "Failed to parse meta JSON at %s (%s); using empty meta.",
                    meta_path, e
                )
                return {}
    except Exception as e:
        logger.exception("Unexpected error reading meta at %s (%s); using empty meta.", meta_path, e)
        return {}

meta: Dict[str, Any] = safe_read_meta(pack.meta_path)

# --------------------------------------------------
# Request Schemas
# --------------------------------------------------
class InferImageReq(BaseModel):
    image_path: str
    return_overlay_png: bool = False

class InferFolderReq(BaseModel):
    folder_path: str
    recursive: bool = True
    limit: Optional[int] = None
    return_overlay_png: bool = False
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None

class ExportCSVReq(BaseModel):
    output_path: str
    predictions: List[Dict[str, Any]]

class ExportJSONReq(BaseModel):
    output_path: str
    predictions: List[Dict[str, Any]]

class ExportAnnotatedImagesReq(BaseModel):
    output_dir: str
    predictions: List[Dict[str, Any]]
    suffix: str = "_annotated"

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def read_image_for_model(img_path: str):
    """
    Read image from disk for model inference.
    - OpenCV loads BGR uint8
    - Convert to RGB (array-based infer_image expects RGB)
    """
    bgr = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(status_code=400, detail=f"Failed to read image via OpenCV: {img_path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return bgr, rgb


def enrich_prediction_with_phenotypes(pred: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute phenotypes from keypoints and add to prediction.
    """
    if not isinstance(pred, dict):
        return pred

    # Extract keypoints
    kpts = pred.get("keypoints", None)
    if kpts is None:
        return pred

    # Handle different keypoint formats
    if isinstance(kpts, list) and len(kpts) > 0:
        # MMPose format: [ [ [x,y], ... ] ] or [ [x,y], ... ]
        if isinstance(kpts[0], (list, tuple)) and len(kpts[0]) > 0 and isinstance(kpts[0][0], (list, tuple)):
            kpts_array = np.array(kpts[0], dtype=np.float32)
        else:
            kpts_array = np.array(kpts, dtype=np.float32)
    else:
        return pred

    if kpts_array.shape[0] < 20:
        return pred

    # Compute phenotypes
    pairs = meta.get("phenotype_pairs", [])
    scale_by_sl = meta.get("phenotype_scale_by_sl", False)
    sl_pair = meta.get("phenotype_sl_pair", None)

    try:
        phenotypes = compute_phenotypes(
            kpts_array,
            pairs=pairs,
            scale_by_sl=scale_by_sl,
            sl_pair=sl_pair,
        )

        # Add phenotypes to extra_pred_fields
        if "extra_pred_fields" not in pred:
            pred["extra_pred_fields"] = {}
        pred["extra_pred_fields"]["phenotypes"] = phenotypes
    except Exception as e:
        logger.warning("Failed to compute phenotypes: %s", e)

    return pred

# --------------------------------------------------
# Endpoints
# --------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "device": DEVICE, "model_dir": str(MODEL_DIR)}

@app.get("/model/info")
def model_info() -> Dict[str, Any]:
    return meta

@app.post("/infer/image")
def infer_one(req: InferImageReq) -> Dict[str, Any]:
    model = manager.load()

    img_path = os.path.abspath(req.image_path)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {img_path}")

    bgr, rgb = read_image_for_model(img_path)

    # Array-based inference (consistent with infer.py Fix 1)
    pred = infer_image(
        model,
        rgb,
        cfg_path=str(pack.config_path),
        device=DEVICE,
    )

    # Ensure caller knows which file produced the prediction
    if isinstance(pred, dict):
        pred.setdefault("image_path", img_path)

    # Enrich with phenotypes
    pred = enrich_prediction_with_phenotypes(pred, meta)

    if req.return_overlay_png:
        tmp_dir = (MODEL_DIR / "tmp").resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)

        out_path = tmp_dir / (Path(img_path).stem + "_overlay.png")
        over = draw_overlay(bgr, pred)
        cv2.imwrite(str(out_path), over)

        if isinstance(pred, dict):
            pred["overlay_path"] = str(out_path)

    return pred

@app.post("/infer/folder")
def infer_folder(req: InferFolderReq) -> Dict[str, Any]:
    model = manager.load()

    folder = os.path.abspath(req.folder_path)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail=f"Path not found: {folder}")

    tmp_dir: Optional[Path] = None
    if req.return_overlay_png:
        tmp_dir = (MODEL_DIR / "tmp").resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)

    preds = []
    for i, p in enumerate(iter_images(folder)):
        bgr, rgb = read_image_for_model(p)

        pred = infer_image(
            model,
            rgb,
            cfg_path=str(pack.config_path),
            device=DEVICE,
        )

        if isinstance(pred, dict):
            pred.setdefault("image_path", p)
            # Add profile information if provided
            if req.profile_id:
                pred["profile_id"] = req.profile_id
            if req.profile_name:
                pred["profile_name"] = req.profile_name

        # Enrich with phenotypes
        pred = enrich_prediction_with_phenotypes(pred, meta)

        if req.return_overlay_png and isinstance(pred, dict) and tmp_dir is not None:
            out_path = tmp_dir / (Path(p).stem + "_overlay.png")
            over = draw_overlay(bgr, pred)
            cv2.imwrite(str(out_path), over)
            pred["overlay_path"] = str(out_path)

        preds.append(pred)

        if req.limit is not None and (i + 1) >= req.limit:
            break

    return {"count": len(preds), "predictions": preds}

# --------------------------------------------------
# Export Endpoints
# --------------------------------------------------
@app.post("/export/csv")
def export_to_csv(req: ExportCSVReq) -> Dict[str, Any]:
    try:
        export_csv(req.output_path, req.predictions, meta)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        logger.exception("CSV export failed")
        raise HTTPException(status_code=500, detail=f"CSV export failed: {e}")

@app.post("/export/json")
def export_to_json(req: ExportJSONReq) -> Dict[str, Any]:
    try:
        export_json(req.output_path, req.predictions)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        logger.exception("JSON export failed")
        raise HTTPException(status_code=500, detail=f"JSON export failed: {e}")

@app.post("/export/annotated-images")
def export_annotated(req: ExportAnnotatedImagesReq) -> Dict[str, Any]:
    try:
        export_annotated_images(req.output_dir, req.predictions, suffix=req.suffix)
        return {"ok": True, "output_dir": req.output_dir}
    except Exception as e:
        logger.exception("Annotated images export failed")
        raise HTTPException(status_code=500, detail=f"Annotated images export failed: {e}")
