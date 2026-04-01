"""
Fishometrics Test Suite — Inference Engine Tests

Validates ONNXInferenceEngine, FallbackPyTorchEngine, and create_engine factory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from inference_runtime.types import ModelMetadata, InferenceResult


def _make_metadata_dict() -> dict:
    return {
        "dataset_name": "TestFish",
        "num_keypoints": 20,
        "keypoint_names": [f"kp{i}" for i in range(20)],
        "codec_input_size": [192, 256],
        "heatmap_size": [48, 64],
        "sigma": 2.0,
        "normalization_mean": [123.675, 116.28, 103.53],
        "normalization_std": [58.395, 57.12, 57.375],
        "bgr_to_rgb": True,
        "padding": 1.25,
        "phenotype_pairs": [[0, 1]],
        "phenotype_names": ["SL"],
        "phenotype_types": ["euclidean"],
        "phenotype_scale_by_sl": False,
        "phenotype_sl_pair": [0, 1],
        "model_version": "cavfish_v1",
        "onnx_opset": 17,
        "export_timestamp": "2024-01-01T00:00:00",
    }


class TestModelMetadata:
    def test_roundtrip(self):
        d = _make_metadata_dict()
        m = ModelMetadata.from_dict(d)
        d2 = m.to_dict()
        m2 = ModelMetadata.from_dict(d2)
        assert m2.dataset_name == m.dataset_name
        assert m2.codec_input_size == m.codec_input_size
        assert m2.heatmap_size == m.heatmap_size
        assert m2.num_keypoints == 20
        assert m2.normalization_mean == m.normalization_mean
        assert m2.padding == m.padding

    def test_defaults(self):
        minimal = {
            "dataset_name": "X",
            "num_keypoints": 5,
            "keypoint_names": ["a", "b", "c", "d", "e"],
            "codec_input_size": [192, 256],
        }
        m = ModelMetadata.from_dict(minimal)
        assert m.sigma == 2.0
        assert m.padding == 1.25
        assert m.heatmap_size == [48, 64]


class TestInferenceResult:
    def test_to_legacy_dict(self):
        from inference_runtime.types import PhenotypeResult

        r = InferenceResult(
            image_path="/img.png",
            keypoints=[[[0.0, 1.0], [2.0, 3.0]]],
            keypoint_scores=[[0.9, 0.8]],
            bboxes=[[0, 0, 100, 100]],
            bbox_scores=[1.0],
            phenotypes=[
                PhenotypeResult(id=0, pair=[0, 1], name="SL", type="euclidean", value_px=50.0, value_norm=None),
            ],
        )
        d = r.to_legacy_dict()
        assert d["image_path"] == "/img.png"
        assert "extra_pred_fields" in d
        assert d["extra_pred_fields"]["phenotypes"][0]["value_px"] == 50.0

    def test_to_legacy_dict_empty_pheno(self):
        r = InferenceResult(
            image_path="", keypoints=[], keypoint_scores=[], bboxes=[], bbox_scores=[]
        )
        d = r.to_legacy_dict()
        assert "extra_pred_fields" not in d


class TestONNXInferenceEngine:
    @pytest.fixture
    def model_dir(self, tmp_path):
        """Prepare a tmp model directory with metadata and dummy ONNX file."""
        meta = _make_metadata_dict()
        (tmp_path / "model_metadata.json").write_text(json.dumps(meta))
        (tmp_path / "model.onnx").write_bytes(b"dummy_onnx_bytes")
        return tmp_path

    def test_engine_load_fails_without_model(self, tmp_path):
        from inference_runtime.inference import ONNXInferenceEngine

        (tmp_path / "model_metadata.json").write_text(json.dumps(_make_metadata_dict()))
        with pytest.raises(FileNotFoundError):
            ONNXInferenceEngine(str(tmp_path / "nonexistent.onnx"), str(tmp_path / "model_metadata.json"))

    @patch("inference_runtime.inference.ort")
    def test_engine_load_with_mock(self, mock_ort, model_dir):
        from inference_runtime.inference import ONNXInferenceEngine

        session = MagicMock()
        session.get_inputs.return_value = [MagicMock(name="input")]
        session.get_outputs.return_value = [MagicMock(name="output")]
        mock_ort.InferenceSession.return_value = session
        mock_ort.SessionOptions.return_value = MagicMock()
        mock_ort.GraphOptimizationLevel.ORT_ENABLE_ALL = 99

        engine = ONNXInferenceEngine(
            str(model_dir / "model.onnx"),
            str(model_dir / "model_metadata.json"),
        )
        assert engine.metadata.num_keypoints == 20
        assert engine.metadata.dataset_name == "TestFish"

    @patch("inference_runtime.inference.ort")
    def test_infer_returns_result(self, mock_ort, model_dir):
        from inference_runtime.inference import ONNXInferenceEngine

        session = MagicMock()
        session.get_inputs.return_value = [MagicMock(name="input")]
        session.get_outputs.return_value = [MagicMock(name="output")]
        session.run.return_value = [np.zeros((1, 20, 64, 48), dtype=np.float32)]
        mock_ort.InferenceSession.return_value = session
        mock_ort.SessionOptions.return_value = MagicMock()
        mock_ort.GraphOptimizationLevel.ORT_ENABLE_ALL = 99

        engine = ONNXInferenceEngine(
            str(model_dir / "model.onnx"),
            str(model_dir / "model_metadata.json"),
        )
        # Set input/output names from mock
        engine.input_name = "input"
        engine.output_name = "output"

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine.infer(image)

        assert isinstance(result, InferenceResult)
        assert len(result.keypoints) == 1
        assert len(result.keypoints[0]) == 20
        assert len(result.keypoint_scores) == 1
        assert len(result.keypoint_scores[0]) == 20


class TestCreateEngine:
    def test_factory_raises_no_artifacts(self, tmp_path):
        """create_engine should raise FileNotFoundError if no model artifacts exist."""
        from inference_runtime.inference import create_engine

        with pytest.raises(FileNotFoundError):
            create_engine(str(tmp_path))

    @patch("inference_runtime.inference.ort")
    def test_factory_prefers_onnx(self, mock_ort, tmp_path):
        """create_engine should prefer ONNX when model.onnx exists."""
        from inference_runtime.inference import create_engine, ONNXInferenceEngine

        (tmp_path / "model_metadata.json").write_text(json.dumps(_make_metadata_dict()))
        (tmp_path / "model.onnx").write_bytes(b"dummy")

        session = MagicMock()
        session.get_inputs.return_value = [MagicMock(name="input")]
        session.get_outputs.return_value = [MagicMock(name="output")]
        mock_ort.InferenceSession.return_value = session
        mock_ort.SessionOptions.return_value = MagicMock()
        mock_ort.GraphOptimizationLevel.ORT_ENABLE_ALL = 99

        engine = create_engine(str(tmp_path))
        assert isinstance(engine, ONNXInferenceEngine)
