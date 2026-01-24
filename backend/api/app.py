# backend/api/app.py
from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import cv2

from backend.cavfish.model_pack import ensure_model_pack, read_meta
from backend.cavfish.manager import ModelManager
from backend.cavfish.infer import infer_image  # array-based infer_image(model, rgb, *, cfg_path=..., device=...)
from backend.cavfish.io import iter_images
from backend.cavfish.draw import draw_overlay

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
    for i, p in enumerate(iter_images(folder, recursive=req.recursive)):
        bgr, rgb = read_image_for_model(p)

        pred = infer_image(
            model,
            rgb,
            cfg_path=str(pack.config_path),
            device=DEVICE,
        )

        if isinstance(pred, dict):
            pred.setdefault("image_path", p)

        if req.return_overlay_png and isinstance(pred, dict) and tmp_dir is not None:
            out_path = tmp_dir / (Path(p).stem + "_overlay.png")
            over = draw_overlay(bgr, pred)
            cv2.imwrite(str(out_path), over)
            pred["overlay_path"] = str(out_path)

        preds.append(pred)

        if req.limit is not None and (i + 1) >= req.limit:
            break

    return {"count": len(preds), "predictions": preds}
