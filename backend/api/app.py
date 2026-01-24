# backend/api/app.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import cv2

from cavfish.model_pack import ensure_model_pack, read_meta
from cavfish.manager import ModelManager
from cavfish.infer import infer_image
from cavfish.io import iter_images
from cavfish.draw import draw_overlay

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # fish-desktop-tool/
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

app = FastAPI()

# Model location (Tauri will set env var or you set default)
MODEL_DIR = Path(os.environ.get("FISH_MODEL_DIR", "models/cavfish_v1")).resolve()
DEVICE = os.environ.get("FISH_DEVICE", "cpu")

pack = ensure_model_pack(MODEL_DIR)
manager = ModelManager(pack, device=DEVICE)


class InferImageReq(BaseModel):
    image_path: str
    return_overlay_png: bool = False  # if true returns path to temp overlay file


class InferFolderReq(BaseModel):
    folder_path: str
    recursive: bool = True
    limit: Optional[int] = None


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "device": DEVICE, "model_dir": str(MODEL_DIR)}


@app.get("/model/info")
def model_info() -> Dict[str, Any]:
    return read_meta(pack.meta_path)


@app.post("/infer/image")
def infer_one(req: InferImageReq) -> Dict[str, Any]:
    loaded = manager.load()
    img_path = os.path.abspath(req.image_path)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {img_path}")

    pred = infer_image(loaded.model, loaded.meta, img_path)

    if req.return_overlay_png:
        # write overlay to a temp file in model_dir/tmp (simple and deterministic)
        tmp_dir = (MODEL_DIR / "tmp").resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out_path = tmp_dir / (Path(img_path).stem + "_overlay.png")

        bgr = cv2.imread(img_path)
        if bgr is None:
            raise HTTPException(status_code=400, detail="Failed to read image via OpenCV")

        over = draw_overlay(bgr, pred)
        cv2.imwrite(str(out_path), over)
        pred["overlay_path"] = str(out_path)

    return pred


@app.post("/infer/folder")
def infer_folder(req: InferFolderReq) -> Dict[str, Any]:
    loaded = manager.load()
    folder = os.path.abspath(req.folder_path)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail=f"Path not found: {folder}")

    preds = []
    for i, p in enumerate(iter_images(folder, recursive=req.recursive)):
        preds.append(infer_image(loaded.model, loaded.meta, p))
        if req.limit is not None and (i + 1) >= req.limit:
            break

    return {"count": len(preds), "predictions": preds}
