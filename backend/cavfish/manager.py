# backend/cavfish/manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import torch
from mmpose.apis import init_model

from .model_pack import ModelPack, read_meta


@dataclass
class LoadedModel:
    model: Any
    meta: Dict[str, Any]


class ModelManager:
    def __init__(self, pack: ModelPack, device: str = "cpu"):
        self.pack = pack
        self.device = device
        self._loaded: Optional[LoadedModel] = None

    def load(self) -> LoadedModel:
        if self._loaded is not None:
            return self._loaded

        meta = read_meta(self.pack.meta_path)

        # Important: for inference, we do NOT need your training-only custom_imports
        # unless the model head class is custom (HeatmapHeadPheno). It is.
        # Therefore: the config import must succeed in runtime.
        # Ensure backend PYTHONPATH includes your custom modules (phenolosses/custom_transforms) or package them.
        model = init_model(
            config=str(self.pack.config_path),
            checkpoint=str(self.pack.weights_path),
            device=self.device,
        )

        # Make sure dataset_meta exists (mmpose expects this in some visualizers/exports).
        # We only set minimal fields we rely on.
        model.dataset_meta = {
            "dataset_name": meta["dataset_name"],
            "num_keypoints": meta["num_keypoints"],
            "keypoint_names": meta["keypoint_names"],
        }

        dev = next(model.parameters()).device
        if dev.type == "cuda" and torch.backends.cudnn.is_available():
            torch.backends.cudnn.benchmark = True

        self._loaded = LoadedModel(model=model, meta=meta)
        return self._loaded
