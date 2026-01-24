# backend/cavfish/infer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

import cv2
import numpy as np
import torch

from mmengine.config import Config
from mmengine.dataset import Compose
from mmengine.registry import init_default_scope
from mmengine.structures import InstanceData
from mmpose.structures import PoseDataSample


# -----------------------------
# JSON serialization utilities
# -----------------------------
def json_sanitize(x: Any) -> Any:
    if x is None or x is Ellipsis:
        return None
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().tolist()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.generic,)):
        return x.item()
    if isinstance(x, dict):
        return {str(k): json_sanitize(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_sanitize(v) for v in x]
    return x


def serialize_pose_data_sample(ds: PoseDataSample) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    metainfo = dict(getattr(ds, "metainfo", {})) if hasattr(ds, "metainfo") else {}
    keep: Dict[str, Any] = {}
    for k in ("dataset_name", "num_keypoints"):
        if k in metainfo:
            keep[k] = metainfo[k]
    out["metainfo"] = json_sanitize(keep)

    pred = getattr(ds, "pred_instances", None)
    if pred is not None:
        for name in ["keypoints", "keypoint_scores", "bboxes", "bbox_scores"]:
            if hasattr(pred, name):
                out[name] = json_sanitize(getattr(pred, name))

        extra: Dict[str, Any] = {}
        for name in dir(pred):
            if name.startswith("_"):
                continue
            if name in {"keypoints", "keypoint_scores", "bboxes", "bbox_scores", "metainfo"}:
                continue
            try:
                val = getattr(pred, name)
            except Exception:
                continue
            if isinstance(val, (torch.Tensor, np.ndarray, np.generic, float, int, list, tuple, dict)):
                extra[name] = json_sanitize(val)

        if extra:
            out["extra_pred_fields"] = extra

    return out


# -----------------------------
# Config bundle + pipeline cache
# -----------------------------
@dataclass
class _InferBundle:
    cfg_path: str
    metainfo: Dict[str, Any]
    input_size: tuple[int, int]  # (W, H)
    padding: float
    pipeline: Compose


_CACHE: Dict[str, _InferBundle] = {}


def _extract_input_size_and_metainfo(cfg: Config) -> tuple[Dict[str, Any], tuple[int, int]]:
    cfg_dict = cfg.to_dict() if hasattr(cfg, "to_dict") else dict(cfg)

    metainfo = cfg_dict.get("metainfo", {}) or {}
    if not isinstance(metainfo, dict):
        metainfo = {}

    codec = cfg_dict.get("codec")
    if not isinstance(codec, dict) or "input_size" not in codec:
        raise KeyError("Config missing codec.input_size")

    inp = codec["input_size"]
    if not isinstance(inp, (list, tuple)) or len(inp) != 2:
        raise ValueError(f"codec.input_size must be (W,H). Got: {inp}")

    input_size = (int(inp[0]), int(inp[1]))  # (W,H)
    return metainfo, input_size


def get_infer_bundle(cfg_path: str) -> _InferBundle:
    if cfg_path in _CACHE:
        return _CACHE[cfg_path]

    # Ensure registries resolve mmpose transforms
    init_default_scope("mmpose")

    cfg = Config.fromfile(cfg_path)
    metainfo, input_size = _extract_input_size_and_metainfo(cfg)

    # Match your demo (you used 1.25)
    padding = 1.25

    # Demo-equivalent inference pipeline
    pipeline_cfg = [
        dict(type="LoadImage"),
        dict(type="GetBBoxCenterScale", padding=padding),
        dict(type="TopdownAffine", input_size=input_size, use_udp=True),
        dict(type="PackPoseInputs"),
    ]
    pipeline = Compose(pipeline_cfg)

    bundle = _InferBundle(
        cfg_path=cfg_path,
        metainfo=metainfo,
        input_size=input_size,
        padding=padding,
        pipeline=pipeline,
    )
    _CACHE[cfg_path] = bundle
    return bundle


# -----------------------------
# Helpers
# -----------------------------
def _full_image_bbox_xyxy_from_shape(h: int, w: int) -> np.ndarray:
    return np.array([0.0, 0.0, float(w), float(h)], dtype=np.float32)


def _ensure_gt_instances(data_sample: PoseDataSample, bbox_xyxy: np.ndarray) -> None:
    """
    Always replace gt_instances with a fresh InstanceData to avoid corrupted
    scalar fields created upstream (which break InstanceData.__len__).
    """
    gt = InstanceData()
    gt.bboxes = np.asarray(bbox_xyxy, dtype=np.float32).reshape(1, 4)     # (1,4)
    gt.bbox_scores = np.asarray([1.0], dtype=np.float32).reshape(1,)      # (1,)
    data_sample.gt_instances = gt


def _prepare_topdown_results_dict(
    rgb: np.ndarray,
    image_path: str = "",
) -> Dict[str, Any]:
    """
    Build dict for topdown transforms.
    IMPORTANT: bbox_center and bbox_scale must be (1,2) to satisfy topdown assertion.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"Expected RGB HxWx3; got {rgb.shape}")

    h, w = rgb.shape[:2]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    bbox_xyxy = _full_image_bbox_xyxy_from_shape(h, w)  # (4,)
    bbox_center = np.array([[w * 0.5, h * 0.5]], dtype=np.float32)         # (1,2)
    bbox_scale = np.array([[float(w), float(h)]], dtype=np.float32)        # (1,2)

    return {
        "img_path": image_path,
        "img": bgr,  # avoid disk IO
        "bbox": bbox_xyxy,
        # safer as per-instance vector
        "bbox_score": np.array([1.0], dtype=np.float32),
        "bbox_center": bbox_center,
        "bbox_scale": bbox_scale,
        "ori_shape": (h, w),
        "img_shape": (h, w),
    }


def _attach_metainfo_and_required_fields(
    sample: PoseDataSample,
    *,
    metainfo: Dict[str, Any],
    input_size: tuple[int, int],
    bbox_xyxy: np.ndarray,
) -> None:
    # Merge config metainfo (keypoint defs) with pipeline-produced metainfo
    if isinstance(metainfo, dict) and metainfo:
        try:
            sample.set_metainfo({**metainfo, **dict(getattr(sample, "metainfo", {}))})
        except Exception:
            pass

    mi = dict(getattr(sample, "metainfo", {})) if hasattr(sample, "metainfo") else {}

    # Required by your fork's TopdownPoseEstimator.add_pred_to_datasample
    if "input_size" not in mi:
        mi["input_size"] = (int(input_size[0]), int(input_size[1]))

    if "input_center" not in mi and "bbox_center" in mi:
        bc = np.array(mi["bbox_center"], dtype=np.float32)
        mi["input_center"] = bc[0] if bc.ndim == 2 else bc

    if "input_scale" not in mi and "bbox_scale" in mi:
        bs = np.array(mi["bbox_scale"], dtype=np.float32)
        mi["input_scale"] = bs[0] if bs.ndim == 2 else bs

    try:
        sample.set_metainfo(mi)
    except Exception:
        pass

    # Never trust pipeline gt_instances; overwrite with clean InstanceData
    _ensure_gt_instances(sample, bbox_xyxy)


# -----------------------------
# Public API
# -----------------------------
def infer_image(
    model,
    image_rgb: np.ndarray,
    *,
    cfg_path: str,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inference matching demo pipeline (GetBBoxCenterScale + TopdownAffine(use_udp=True)),
    without relying on model.cfg.
    """
    bundle = get_infer_bundle(cfg_path)

    if device is not None:
        model.to(device)
    model.eval()

    h, w = image_rgb.shape[:2]
    bbox_xyxy = _full_image_bbox_xyxy_from_shape(h, w)

    data = _prepare_topdown_results_dict(image_rgb, image_path="")
    processed = bundle.pipeline(data)

    inputs = processed.get("inputs", None)
    data_samples = processed.get("data_samples", None)

    # Normalize to lists
    if isinstance(inputs, torch.Tensor):
        inputs_list = [inputs]
    elif isinstance(inputs, (list, tuple)):
        inputs_list = list(inputs)
    else:
        return {"error": f"Pipeline did not produce inputs. Got {type(inputs)}"}

    if isinstance(data_samples, PoseDataSample):
        samples_list = [data_samples]
    elif isinstance(data_samples, (list, tuple)):
        samples_list = list(data_samples)
    else:
        return {"error": f"Pipeline did not produce data_samples. Got {type(data_samples)}"}

    for s in samples_list:
        _attach_metainfo_and_required_fields(
            s,
            metainfo=bundle.metainfo,
            input_size=bundle.input_size,
            bbox_xyxy=bbox_xyxy,
        )

    # Move inputs to model device
    model_device = next(model.parameters()).device
    inputs_list = [x.to(model_device) for x in inputs_list]

    batch = {"inputs": inputs_list, "data_samples": samples_list}

    # Note: test_step handles preprocessing internally, so don't call data_preprocessor here
    with torch.no_grad():
        outputs = model.test_step(batch)

    if isinstance(outputs, (list, tuple)) and len(outputs) > 0 and isinstance(outputs[0], PoseDataSample):
        return serialize_pose_data_sample(outputs[0])

    return {"error": "Unexpected outputs from model.test_step", "outputs_type": str(type(outputs)), "raw": str(outputs)}


def infer_image_path(
    model,
    image_path: str,
    *,
    cfg_path: str,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if bgr is None:
        return {"image_path": image_path, "error": f"Failed to read image: {image_path}"}

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pred = infer_image(model, rgb, cfg_path=cfg_path, device=device)
    if isinstance(pred, dict):
        pred.setdefault("image_path", image_path)
    return pred


def infer_images(
    model,
    cfg_path: str,
    image_paths: Union[str, Sequence[str]],
    *,
    device: Optional[str] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    single = isinstance(image_paths, str)
    paths = [image_paths] if single else list(image_paths)

    outs: List[Dict[str, Any]] = []
    for p in paths:
        outs.append(infer_image_path(model, p, cfg_path=cfg_path, device=device))

    return outs[0] if single else outs
