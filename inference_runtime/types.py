# Inference Runtime — Types
"""
Data types for the Fishometrics inference runtime.
These types define the contract between the Tauri frontend and the inference backend,
independent of any ML framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetadata:
    """Metadata describing the exported model and its expected inputs/outputs."""
    dataset_name: str
    num_keypoints: int
    keypoint_names: List[str]
    codec_input_size: List[int]  # [W, H] = [192, 256]
    heatmap_size: List[int]  # [W, H] = [48, 64]
    sigma: float
    normalization_mean: List[float]  # BGR order: [123.675, 116.28, 103.53]
    normalization_std: List[float]   # BGR order: [58.395, 57.12, 57.375]
    bgr_to_rgb: bool
    padding: float  # bbox padding factor (1.25)
    phenotype_pairs: List[List[int]]
    phenotype_names: List[str]
    phenotype_types: List[str]
    phenotype_scale_by_sl: bool
    phenotype_sl_pair: Optional[List[int]]
    model_version: str = "cavfish_v1"
    onnx_opset: int = 17
    export_timestamp: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelMetadata":
        return cls(
            dataset_name=d["dataset_name"],
            num_keypoints=d["num_keypoints"],
            keypoint_names=d["keypoint_names"],
            codec_input_size=d["codec_input_size"],
            heatmap_size=d.get("heatmap_size", [48, 64]),
            sigma=d.get("sigma", 2.0),
            normalization_mean=d.get("normalization_mean", [123.675, 116.28, 103.53]),
            normalization_std=d.get("normalization_std", [58.395, 57.12, 57.375]),
            bgr_to_rgb=d.get("bgr_to_rgb", True),
            padding=d.get("padding", 1.25),
            phenotype_pairs=d.get("phenotype_pairs", []),
            phenotype_names=d.get("phenotype_names", []),
            phenotype_types=d.get("phenotype_types", []),
            phenotype_scale_by_sl=d.get("phenotype_scale_by_sl", False),
            phenotype_sl_pair=d.get("phenotype_sl_pair"),
            model_version=d.get("model_version", "cavfish_v1"),
            onnx_opset=d.get("onnx_opset", 17),
            export_timestamp=d.get("export_timestamp", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "num_keypoints": self.num_keypoints,
            "keypoint_names": self.keypoint_names,
            "codec_input_size": self.codec_input_size,
            "heatmap_size": self.heatmap_size,
            "sigma": self.sigma,
            "normalization_mean": self.normalization_mean,
            "normalization_std": self.normalization_std,
            "bgr_to_rgb": self.bgr_to_rgb,
            "padding": self.padding,
            "phenotype_pairs": self.phenotype_pairs,
            "phenotype_names": self.phenotype_names,
            "phenotype_types": self.phenotype_types,
            "phenotype_scale_by_sl": self.phenotype_scale_by_sl,
            "phenotype_sl_pair": self.phenotype_sl_pair,
            "model_version": self.model_version,
            "onnx_opset": self.onnx_opset,
            "export_timestamp": self.export_timestamp,
        }


@dataclass
class InferenceRequest:
    """A single image inference request."""
    image_path: str
    return_overlay: bool = False


@dataclass
class KeypointResult:
    """Result for a single detected instance."""
    keypoints: List[List[float]]       # K x 2 (x, y in original image coords)
    keypoint_scores: List[float]       # K confidence scores
    bbox: List[float]                  # [x1, y1, x2, y2]
    bbox_score: float = 1.0


@dataclass
class PhenotypeResult:
    """A single phenotype measurement."""
    id: int
    pair: List[int]
    name: str
    type: str  # 'xy', 'x', or 'y'
    value_px: float
    value_norm: Optional[float]


@dataclass
class InferenceResult:
    """Complete inference result for one image."""
    image_path: str
    keypoints: List[List[float]]        # [N][K][2] — outer list is instances
    keypoint_scores: List[List[float]]  # [N][K]
    bboxes: List[List[float]]           # [N][4]
    bbox_scores: List[float]            # [N]
    phenotypes: List[PhenotypeResult] = field(default_factory=list)
    overlay_png_base64: Optional[str] = None
    error: Optional[str] = None

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to the legacy API response format for backward compatibility."""
        result: Dict[str, Any] = {
            "image_path": self.image_path,
            "keypoints": self.keypoints,
            "keypoint_scores": self.keypoint_scores,
            "bboxes": self.bboxes,
            "bbox_scores": self.bbox_scores,
        }
        if self.phenotypes:
            result["extra_pred_fields"] = {
                "phenotypes": [
                    {
                        "id": p.id,
                        "pair": p.pair,
                        "name": p.name,
                        "type": p.type,
                        "value_px": p.value_px,
                        "value_norm": p.value_norm,
                    }
                    for p in self.phenotypes
                ]
            }
        if self.overlay_png_base64:
            result["overlay_png_base64"] = self.overlay_png_base64
        if self.error:
            result["error"] = self.error
        return result
