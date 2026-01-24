# backend/cavfish/model_pack.py
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


@dataclass(frozen=True)
class ModelPack:
    model_dir: Path
    config_path: Path
    weights_path: Path
    meta_path: Path


def load_py_config(config_path: Path) -> Dict[str, Any]:
    """Import an MMEngine-style config python file as a module and return its globals."""
    spec = importlib.util.spec_from_file_location("cavfish_config", str(config_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import config: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {k: getattr(module, k) for k in dir(module) if not k.startswith("__")}


def metainfo_to_keypoint_names(metainfo: Dict[str, Any]) -> List[str]:
    kp_info = metainfo.get("keypoint_info", {})
    # keypoint_info is dict like {0: {name: kp1}, 1: {name: kp2}, ...}
    # ensure sorted by id
    names = []
    for kid in sorted(kp_info.keys()):
        names.append(kp_info[kid].get("name", f"kp{kid+1}"))
    return names


def build_meta_from_config(cfg_globals: Dict[str, Any]) -> Dict[str, Any]:
    metainfo = cfg_globals.get("metainfo")
    if not isinstance(metainfo, dict):
        raise ValueError("Config must define `metainfo = dict(...)`")

    num_kp = metainfo.get("num_keypoints")
    if num_kp != 20:
        raise ValueError(f"Expected num_keypoints=20, got {num_kp}")

    keypoint_names = metainfo_to_keypoint_names(metainfo)
    if len(keypoint_names) != 20:
        raise ValueError(f"Expected 20 keypoint names, got {len(keypoint_names)}")

    codec = cfg_globals.get("codec", {})
    input_size = codec.get("input_size", (192, 256))  # (w,h)
    if not (isinstance(input_size, (list, tuple)) and len(input_size) == 2):
        raise ValueError(f"Invalid codec.input_size: {input_size}")

    model = cfg_globals.get("model", {})
    head = (model or {}).get("head", {})
    loss_pheno = (head or {}).get("loss_pheno", {})
    pairs = loss_pheno.get("pairs", [])
    if not pairs:
        # still allow empty pairs
        pairs = []
    # Normalize pairs to list of [i,j]
    pairs_norm: List[List[int]] = []
    for p in pairs:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            raise ValueError(f"Invalid phenotype pair: {p}")
        i, j = int(p[0]), int(p[1])
        pairs_norm.append([i, j])

    # Capture phenotype normalization intent (from your training loss settings)
    degree_normalize = bool(loss_pheno.get("degree_normalize", False))
    scale_by_sl = bool(loss_pheno.get("scale_by_SL", False))

    # Heuristic: choose SL pair if scale_by_SL is true.
    # Your config includes (0,3) among pairs and you used it in discussions as a plausible “standard length”.
    # You can change this later by editing meta.json.
    sl_pair = [0, 3] if scale_by_sl else None

    return {
        "dataset_name": metainfo.get("dataset_name", "fish_20kpt"),
        "num_keypoints": 20,
        "keypoint_names": keypoint_names,
        "codec_input_size": [int(input_size[0]), int(input_size[1])],  # [w,h]
        "phenotype_pairs": pairs_norm,
        "phenotype_degree_normalize": degree_normalize,
        "phenotype_scale_by_sl": scale_by_sl,
        "phenotype_sl_pair": sl_pair,  # can be null
    }


def ensure_model_pack(model_dir: Path) -> ModelPack:
    model_dir = model_dir.resolve()
    config_path = model_dir / "config.py"
    weights_path = model_dir / "weights.pth"
    meta_path = model_dir / "meta.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Missing config.py in {model_dir}")
    if not weights_path.exists():
        raise FileNotFoundError(f"Missing weights.pth in {model_dir}")

    if not meta_path.exists():
        cfg = load_py_config(config_path)
        meta = build_meta_from_config(cfg)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return ModelPack(
        model_dir=model_dir,
        config_path=config_path,
        weights_path=weights_path,
        meta_path=meta_path,
    )


def read_meta(meta_path: Path) -> Dict[str, Any]:
    return json.loads(meta_path.read_text(encoding="utf-8"))

