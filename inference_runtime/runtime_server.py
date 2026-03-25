# Inference Runtime — Lightweight FastAPI Server
"""
Drop-in replacement for backend/api/app.py that uses ONNX Runtime
instead of the full MMPose stack.

Preserves the same HTTP API contract so the Tauri frontend works unchanged.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent dir to path for imports
_THIS_DIR = Path(__file__).resolve().parent
_ROOT = _THIS_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from inference_runtime.inference import create_engine
from inference_runtime.types import InferenceResult

logger = logging.getLogger("phenoai.runtime")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

# --------------------------------------------------
# Config from environment
# --------------------------------------------------
MODEL_DIR = Path(os.environ.get("FISH_MODEL_DIR", os.environ.get("PHENOAI_MODEL_DIR", "models/cavfish_v1"))).resolve()
DEVICE = os.environ.get("FISH_DEVICE", os.environ.get("PHENOAI_DEVICE", "cpu"))
FORCE_LEGACY = os.environ.get("PHENOAI_USE_LEGACY", "").strip() == "1"

logger.info("Model dir: %s", MODEL_DIR)
logger.info("Device: %s", DEVICE)

# --------------------------------------------------
# Engine initialization
# --------------------------------------------------
engine = create_engine(str(MODEL_DIR), device=DEVICE, force_legacy=FORCE_LEGACY)
meta = engine.get_metadata_dict()

# --------------------------------------------------
# FastAPI app
# --------------------------------------------------
app = FastAPI(title="PhenoAI Inference Runtime")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request schemas (same as legacy)
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
# Drawing (reuse from backend, or inline minimal version)
# --------------------------------------------------
def _draw_overlay(bgr: np.ndarray, pred: Dict[str, Any]) -> np.ndarray:
    """Draw keypoints on image. Reuses backend.cavfish.draw if available, else inline."""
    try:
        from backend.cavfish.draw import draw_overlay
        return draw_overlay(bgr, pred)
    except ImportError:
        pass

    # Inline minimal drawing
    out = bgr.copy()
    kpts = pred.get("keypoints", [])
    scores = pred.get("keypoint_scores", [])

    if isinstance(kpts, list) and len(kpts) > 0:
        if isinstance(kpts[0], list) and len(kpts[0]) > 0 and isinstance(kpts[0][0], list):
            kpts = kpts[0]
        if isinstance(scores, list) and len(scores) > 0 and isinstance(scores[0], list):
            scores = scores[0]

    h, w = out.shape[:2]
    radius = max(3, int(min(h, w) * 0.007))

    for i, xy in enumerate(kpts):
        if not isinstance(xy, (list, tuple)) or len(xy) < 2:
            continue
        x, y = float(xy[0]), float(xy[1])
        s = float(scores[i]) if i < len(scores) else 1.0
        if s < 0.05 or not np.isfinite(x) or not np.isfinite(y):
            continue
        cv2.circle(out, (int(round(x)), int(round(y))), radius, (0, 0, 255), -1, cv2.LINE_AA)
        label = str(i + 1)  # 1-based
        font_scale = max(0.5, min(h, w) * 0.001)
        font_thick = max(2, int(min(h, w) * 0.003))
        offset_y = int(radius * 2.5)
        pt = (int(round(x)) - 5, int(round(y)) - offset_y)
        cv2.putText(out, label, pt, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), font_thick + 1, cv2.LINE_AA)
        cv2.putText(out, label, pt, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

    return out


# --------------------------------------------------
# Export helpers (reuse from backend)
# --------------------------------------------------
def _export_csv(path: str, predictions: list, meta_dict: dict):
    try:
        from backend.cavfish.export import export_csv
        export_csv(path, predictions, meta_dict)
        return
    except ImportError:
        pass

    # Inline structured CSV export (mirrors backend/cavfish/export.py)
    import csv as _csv
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not predictions:
        return

    first_pred = predictions[0]

    # Determine keypoint column names from first prediction
    kpts_first = first_pred.get("keypoints", [])
    if isinstance(kpts_first, list) and kpts_first and isinstance(kpts_first[0], dict):
        # Dict format (profile-filtered): [{x, y, name, score}, ...]
        kp_names = [kpt.get("name", f"kp{i + 1}") for i, kpt in enumerate(kpts_first)]
    else:
        # Array format: flatten [[[x,y],...]] → [[x,y],...]
        if (isinstance(kpts_first, list) and kpts_first
                and isinstance(kpts_first[0], list) and kpts_first[0]
                and isinstance(kpts_first[0][0], list)):
            kpts_first = kpts_first[0]
        kp_names = [f"kp{i + 1}" for i in range(len(kpts_first))]

    # Phenotype columns from first prediction (already profile-filtered)
    phenotypes_first = first_pred.get("extra_pred_fields", {}).get("phenotypes", [])

    fieldnames = ["image_path"]
    for name in kp_names:
        fieldnames.extend([f"{name}_x", f"{name}_y"])
    for ph in phenotypes_first:
        fieldnames.append(f"{ph.get('name', f'pheno_{ph.get(chr(105), 0)}')}_px")

    with open(path, "w", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pred in predictions:
            row: dict = {"image_path": pred.get("image_path", "")}

            kpts = pred.get("keypoints", [])

            if isinstance(kpts, list) and kpts and isinstance(kpts[0], dict):
                # Dict format (profile-filtered keypoints)
                for i, name in enumerate(kp_names):
                    if i < len(kpts):
                        row[f"{name}_x"] = float(kpts[i].get("x", "")) if kpts[i].get("x") is not None else ""
                        row[f"{name}_y"] = float(kpts[i].get("y", "")) if kpts[i].get("y") is not None else ""
                    else:
                        row[f"{name}_x"] = ""
                        row[f"{name}_y"] = ""
            else:
                # Array format: flatten if nested
                if (isinstance(kpts, list) and kpts
                        and isinstance(kpts[0], list) and kpts[0]
                        and isinstance(kpts[0][0], list)):
                    kpts = kpts[0]
                for i, name in enumerate(kp_names):
                    if i < len(kpts):
                        kpt = kpts[i]
                        if isinstance(kpt, (list, tuple)) and len(kpt) >= 2:
                            row[f"{name}_x"] = float(kpt[0])
                            row[f"{name}_y"] = float(kpt[1])
                        else:
                            row[f"{name}_x"] = ""
                            row[f"{name}_y"] = ""
                    else:
                        row[f"{name}_x"] = ""
                        row[f"{name}_y"] = ""

            for ph in pred.get("extra_pred_fields", {}).get("phenotypes", []):
                col = f"{ph.get('name', f'pheno_{ph.get(chr(105), 0)}')}_px"
                if col in fieldnames:
                    row[col] = ph.get("value_px", "")

            writer.writerow(row)


def _export_json(path: str, predictions: list):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # Strip value_norm from phenotypes before writing
    clean = []
    for pred in predictions:
        p = dict(pred)
        extra = p.get("extra_pred_fields")
        if extra:
            extra = dict(extra)
            if extra.get("phenotypes"):
                extra["phenotypes"] = [{k: v for k, v in ph.items() if k != "value_norm"} for ph in extra["phenotypes"]]
            p["extra_pred_fields"] = extra
        clean.append(p)
    with open(path, "w") as f:
        json.dump(clean, f, indent=2)


def _export_annotated_images(output_dir: str, predictions: list, suffix: str = "_annotated"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for pred in predictions:
        image_path = pred.get("image_path", "")
        if not image_path or not Path(image_path).exists():
            continue
        bgr = cv2.imread(image_path)
        if bgr is None:
            continue
        overlay = _draw_overlay(bgr, pred)
        stem = Path(image_path).stem
        out_file = output_path / f"{stem}{suffix}.jpg"
        cv2.imwrite(str(out_file), overlay, [cv2.IMWRITE_JPEG_QUALITY, 95])


# --------------------------------------------------
# Image iteration
# --------------------------------------------------
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

def _iter_images(root: str):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if Path(fn).suffix.lower() in IMAGE_EXTS:
                yield os.path.join(dirpath, fn)


# --------------------------------------------------
# Prediction enrichment
# --------------------------------------------------
def _enrich_with_phenotypes(pred: Dict[str, Any]) -> Dict[str, Any]:
    """Phenotypes are already computed by the engine. This is for legacy compatibility."""
    return pred


def _result_to_response(result: InferenceResult) -> Dict[str, Any]:
    """Convert InferenceResult to legacy API response format."""
    return result.to_legacy_dict()


# --------------------------------------------------
# Memory-efficient image loading
# --------------------------------------------------
_JPEG_EXTS = frozenset({".jpg", ".jpeg"})
_INFER_MAX = 2048  # max dimension (px) for inference — far above model input size


def _read_for_inference(p: str):
    """Load image at reduced resolution where possible.

    For JPEG files, OpenCV's IMREAD_REDUCED_COLOR_4 instructs the JPEG
    codec to decode at 1/4 linear resolution, so a 6000×4000 photo
    returns a 1500×1000 array — never allocating the ~130 MB full-res
    buffer. For other formats (TIFF, PNG, BMP) we read full-res and
    immediately resize if the image exceeds _INFER_MAX.

    Returns:
        (bgr_array, scale_factor)  where original_coord = infer_coord * scale_factor.
        Returns (None, 1.0) if the image cannot be read.
    """
    ext = Path(p).suffix.lower()
    if ext in _JPEG_EXTS:
        bgr4 = cv2.imread(p, cv2.IMREAD_REDUCED_COLOR_4)
        if bgr4 is not None:
            return bgr4, 4.0
        # Tiny JPEG or read failure — fall through to full-res read
    bgr = cv2.imread(p, cv2.IMREAD_COLOR)
    if bgr is None:
        return None, 1.0
    h, w = bgr.shape[:2]
    if max(h, w) > _INFER_MAX:
        s = _INFER_MAX / max(h, w)
        bgr_small = cv2.resize(
            bgr, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA
        )
        del bgr
        return bgr_small, 1.0 / s
    return bgr, 1.0


def _scale_resp_to_original(resp: Dict[str, Any], scale: float) -> None:
    """Scale keypoint coordinates and phenotype pixel distances in-place
    from inference-image space back to original-image space.
    Call this after inference when scale_factor != 1.0.
    """
    if scale == 1.0:
        return
    kpts = resp.get("keypoints")
    if kpts:
        if isinstance(kpts[0], list) and kpts[0] and isinstance(kpts[0][0], list):
            resp["keypoints"] = [[[c * scale for c in xy] for xy in fr] for fr in kpts]
        elif isinstance(kpts[0], (list, tuple)):
            resp["keypoints"] = [[c * scale for c in xy] for xy in kpts]
    phenotypes = (resp.get("extra_pred_fields") or {}).get("phenotypes")
    if phenotypes:
        for ph in phenotypes:
            if "value_px" in ph:
                ph["value_px"] = ph["value_px"] * scale
    bboxes = resp.get("bboxes")
    if bboxes:
        resp["bboxes"] = [[c * scale for c in box] for box in bboxes]


# --------------------------------------------------
# Endpoints (same contract as legacy backend)
# --------------------------------------------------
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "phenoai-inference-runtime",
        "runtime": "onnx" if not FORCE_LEGACY else "legacy",
        "endpoints": ["/health", "/model/info", "/infer/image", "/infer/folder"],
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "device": DEVICE, "model_dir": str(MODEL_DIR)}


@app.get("/model/info")
def model_info() -> Dict[str, Any]:
    return meta


@app.post("/infer/image")
def infer_one(req: InferImageReq) -> Dict[str, Any]:
    img_path = os.path.abspath(req.image_path)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail=f"Image not found: {img_path}")

    # Read at reduced resolution (never allocates full-res array for large JPEGs)
    bgr, infer_scale = _read_for_inference(img_path)
    if bgr is None:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {img_path}")

    result = engine.infer(bgr)
    result.image_path = img_path
    resp = _result_to_response(result)

    if req.return_overlay_png:
        # bgr is already at reduced resolution (≤ 2048px).
        # If it still exceeds the preview cap, resize further for overlay.
        _MAX_OV = 1200
        h_bgr, w_bgr = bgr.shape[:2]
        if max(h_bgr, w_bgr) > _MAX_OV:
            _ov_s = _MAX_OV / max(h_bgr, w_bgr)
            bgr_draw = cv2.resize(
                bgr,
                (max(1, int(w_bgr * _ov_s)), max(1, int(h_bgr * _ov_s))),
                interpolation=cv2.INTER_AREA,
            )
            del bgr
            # Keypoints are in infer-image coords; scale to bgr_draw coords for drawing
            _kpts = resp.get("keypoints", [])
            if _kpts:
                if isinstance(_kpts[0], list) and _kpts[0] and isinstance(_kpts[0][0], list):
                    resp_draw = {**resp, "keypoints": [[[c * _ov_s for c in xy] for xy in fr] for fr in _kpts]}
                else:
                    resp_draw = {**resp, "keypoints": [[c * _ov_s for c in xy] for xy in _kpts]}
            else:
                resp_draw = resp
        else:
            bgr_draw = bgr
            del bgr
            resp_draw = resp
        overlay = _draw_overlay(bgr_draw, resp_draw)
        del bgr_draw
        if resp_draw is not resp:
            del resp_draw

        # Scale keypoints to original-image coordinates now that drawing is done
        _scale_resp_to_original(resp, infer_scale)

        tmp_dir = (MODEL_DIR / "tmp").resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(img_path).stem

        # Save overlay to disk
        out_path = tmp_dir / (stem + "_overlay.jpg")
        cv2.imwrite(str(out_path), overlay, [cv2.IMWRITE_JPEG_QUALITY, 95])
        resp["overlay_path"] = str(out_path)

        # Medium preview for display (max 800px wide, JPEG q65)
        h_ov, w_ov = overlay.shape[:2]
        _pw = 800
        if w_ov > _pw:
            _ph = max(1, int(_pw * h_ov / w_ov))
            preview = cv2.resize(overlay, (_pw, _ph), interpolation=cv2.INTER_AREA)
        else:
            preview = overlay
        _, prev_buf = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 65])
        resp["overlay_preview_base64"] = base64.b64encode(prev_buf).decode("utf-8")
        del preview, prev_buf

        # Thumbnail for sidebar strip.
        # Never upscale: keep native size if overlay is already <= 160 px wide.
        # Use INTER_AREA for large downscales, INTER_CUBIC for small ones.
        _tw = min(w_ov, 160)
        _th = max(1, int(_tw * h_ov / w_ov))
        if w_ov > _tw:
            _interp = cv2.INTER_AREA if w_ov > _tw * 2 else cv2.INTER_CUBIC
            thumb = cv2.resize(overlay, (_tw, _th), interpolation=_interp)
        else:
            thumb = overlay
        _, thumb_buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 70])
        resp["overlay_thumbnail_base64"] = base64.b64encode(thumb_buf).decode("utf-8")
        del overlay, thumb, thumb_buf
    else:
        del bgr
        _scale_resp_to_original(resp, infer_scale)

    resp["file_size"] = os.path.getsize(img_path)
    return resp


@app.post("/infer/folder")
def infer_folder(req: InferFolderReq) -> Dict[str, Any]:
    folder = os.path.abspath(req.folder_path)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail=f"Path not found: {folder}")

    tmp_dir = None
    if req.return_overlay_png:
        tmp_dir = (MODEL_DIR / "tmp").resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)

    import gc
    preds = []
    for i, p in enumerate(_iter_images(folder)):
        # Read at reduced resolution — for JPEG this avoids ever allocating the
        # full-res array (e.g. 8 MB instead of 130 MB for a 35 MP camera photo).
        bgr, infer_scale = _read_for_inference(p)
        if bgr is None:
            continue

        result = engine.infer(bgr)
        result.image_path = p
        resp = _result_to_response(result)
        # resp["keypoints"] are in infer-image coordinates at this point.

        if req.profile_id:
            resp["profile_id"] = req.profile_id
        if req.profile_name:
            resp["profile_name"] = req.profile_name

        if req.return_overlay_png and tmp_dir:
            # bgr is already at ≤ 2048 px.  Cap further to 1200 px for the overlay
            # so the thumbnail/preview stay small.
            _MAX_OV = 1200
            h_bgr, w_bgr = bgr.shape[:2]
            if max(h_bgr, w_bgr) > _MAX_OV:
                _ov_s = _MAX_OV / max(h_bgr, w_bgr)
                bgr_draw = cv2.resize(
                    bgr,
                    (max(1, int(w_bgr * _ov_s)), max(1, int(h_bgr * _ov_s))),
                    interpolation=cv2.INTER_AREA,
                )
                del bgr
                # Scale keypoints from infer coords to bgr_draw coords for drawing
                _kpts = resp.get("keypoints", [])
                if _kpts:
                    if isinstance(_kpts[0], list) and _kpts[0] and isinstance(_kpts[0][0], list):
                        resp_draw = {**resp, "keypoints": [[[c * _ov_s for c in xy] for xy in fr] for fr in _kpts]}
                    else:
                        resp_draw = {**resp, "keypoints": [[c * _ov_s for c in xy] for xy in _kpts]}
                else:
                    resp_draw = resp
            else:
                bgr_draw = bgr
                del bgr
                resp_draw = resp
            overlay = _draw_overlay(bgr_draw, resp_draw)
            del bgr_draw
            if resp_draw is not resp:
                del resp_draw

            # Scale keypoints to original-image coordinates
            _scale_resp_to_original(resp, infer_scale)

            stem = Path(p).stem

            # Save overlay to disk (at capped resolution)
            out_path = tmp_dir / (stem + "_overlay.jpg")
            cv2.imwrite(str(out_path), overlay, [cv2.IMWRITE_JPEG_QUALITY, 95])
            resp["overlay_path"] = str(out_path)

            # Thumbnail for sidebar strip.
            # Never upscale: keep native size if overlay is already <= 160 px wide.
            # Use INTER_AREA for large downscales, INTER_CUBIC for small ones.
            h_ov, w_ov = overlay.shape[:2]
            _tw = min(w_ov, 160)
            _th = max(1, int(_tw * h_ov / w_ov))
            if w_ov > _tw:
                _interp = cv2.INTER_AREA if w_ov > _tw * 2 else cv2.INTER_CUBIC
                thumb = cv2.resize(overlay, (_tw, _th), interpolation=_interp)
            else:
                thumb = overlay
            _, thumb_buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 70])
            resp["overlay_thumbnail_base64"] = base64.b64encode(thumb_buf).decode("utf-8")
            del overlay, thumb, thumb_buf
            # overlay_preview_base64 intentionally omitted from the folder batch.
            # The frontend lazy-loads it from overlay_path when the user selects a result.
        else:
            del bgr
            _scale_resp_to_original(resp, infer_scale)

        resp["file_size"] = os.path.getsize(p)
        preds.append(resp)
        if req.limit is not None and (i + 1) >= req.limit:
            break
        # Hint GC every 10 images to release numpy/OpenCV memory pools
        if i % 10 == 9:
            gc.collect()

    gc.collect()
    return {"count": len(preds), "predictions": preds}


# --------------------------------------------------
# Export endpoints
# --------------------------------------------------
@app.post("/export/csv")
def export_to_csv(req: ExportCSVReq) -> Dict[str, Any]:
    try:
        _export_csv(req.output_path, req.predictions, meta)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/json")
def export_to_json(req: ExportJSONReq) -> Dict[str, Any]:
    try:
        _export_json(req.output_path, req.predictions)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/annotated-images")
def export_annotated(req: ExportAnnotatedImagesReq) -> Dict[str, Any]:
    try:
        _export_annotated_images(req.output_dir, req.predictions, req.suffix)
        return {"ok": True, "output_dir": req.output_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# CLI entry point
# --------------------------------------------------
def main():
    import uvicorn

    port = int(os.environ.get("FISH_PORT", os.environ.get("PHENOAI_PORT", "8008")))
    host = os.environ.get("PHENOAI_HOST", "127.0.0.1")

    logger.info("Starting PhenoAI inference runtime on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
