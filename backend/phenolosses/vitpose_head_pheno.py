from __future__ import annotations

from typing import List, Optional, Tuple

from torch import Tensor

from mmpose.registry import MODELS
from backend.third_party.mmpose.heatmap_head import CavfishHeatmapHead


@MODELS.register_module()
class HeatmapHeadPheno(CavfishHeatmapHead):
    """HeatmapHead + additional phenotype loss term."""

    def __init__(self, loss_pheno: dict, alpha_pheno: float = 1e-2, **kwargs):
        super().__init__(**kwargs)
        self.loss_pheno = MODELS.build(loss_pheno)
        self.alpha_pheno = float(alpha_pheno)

    def loss_by_feat(
        self,
        preds: Tuple[Tensor] | Tensor,
        data_samples: Optional[List] = None,
    ):
        # Base heatmap losses (MSE + whatever HeatmapHead does)
        losses = super().loss_by_feat(preds, data_samples)

        # Pred heatmaps tensor
        pred = preds[0] if isinstance(preds, (list, tuple)) else preds

        # Optional heatmap size from metainfo (may be None)
        hm_size = None
        if data_samples:
            meta0 = getattr(data_samples[0], "metainfo", {}) or {}
            hm_size = meta0.get("heatmap_size", None)

        loss_ph = self.loss_pheno(
            pred_heatmaps=pred,
            data_samples=data_samples,
            heatmap_size=hm_size,
        )
        losses["loss_pheno"] = self.alpha_pheno * loss_ph
        return losses
