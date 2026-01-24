# backend/cavfish/manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any

from mmengine.config import Config
from mmengine.runner import load_checkpoint
from mmengine.registry import init_default_scope

import torch

from mmpose.utils.setup_env import register_all_modules

# 1) Register MMPose modules
register_all_modules(init_default_scope=False)
init_default_scope("mmpose")

# 2) Register YOUR custom modules
import custom_transforms  # noqa: F401
import phenolosses.vitpose_head_pheno  # noqa: F401
import phenolosses.phenotype_distance_loss  # noqa: F401

# 3) CRITICAL: force-import all loss submodules so @MODELS.register_module runs
import importlib
import pkgutil
import mmpose.models.losses as losses_pkg

for m in pkgutil.iter_modules(losses_pkg.__path__):
    importlib.import_module(f"{losses_pkg.__name__}.{m.name}")

# Only now import MODELS and build
from mmpose.registry import MODELS  # noqa: E402


def build_model_from_cfg(cfg_path: str, checkpoint_path: str, device: str = "cpu"):
    cfg = Config.fromfile(cfg_path)
    model = MODELS.build(cfg.model)

    # Attach cfg like init_model does (many utilities assume it exists)
    model.cfg = cfg

    # Attach dataset_meta if available (demo patches this explicitly)
    if hasattr(cfg, "metainfo"):
        model.dataset_meta = cfg.metainfo

    load_checkpoint(model, checkpoint_path, map_location="cpu")
    model.to(device)
    model.eval()
    return model



@dataclass
class ModelManager:
    cfg_path: str
    checkpoint_path: str
    device: str = "cpu"

    _model: Optional[Any] = None

    def load(self):
        if self._model is None:
            self._model = build_model_from_cfg(
                self.cfg_path, self.checkpoint_path, self.device
            )
        return self._model

    @property
    def model(self):
        if self._model is None:
            raise RuntimeError("Model not loaded. Call manager.load() first.")
        return self._model
