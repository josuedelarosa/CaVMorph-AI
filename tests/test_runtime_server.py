"""
Fishometrics Test Suite — Runtime Server Smoke Tests

Validates the FastAPI endpoints exposed by inference_runtime.runtime_server.
These tests mock the engine to avoid needing real model artifacts.
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

from inference_runtime.types import InferenceResult, PhenotypeResult


def _make_mock_engine():
    engine = MagicMock()
    engine.get_metadata_dict.return_value = {
        "dataset_name": "TestFish",
        "num_keypoints": 20,
        "model_version": "cavfish_v1",
    }

    result = InferenceResult(
        image_path="",
        keypoints=[[[float(i), float(i)] for i in range(20)]],
        keypoint_scores=[[0.95] * 20],
        bboxes=[[0.0, 0.0, 640.0, 480.0]],
        bbox_scores=[1.0],
        phenotypes=[
            PhenotypeResult(id=0, pair=[0, 1], name="SL", type="euclidean", value_px=100.0, value_norm=None),
        ],
    )
    engine.infer.return_value = result
    return engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Import runtime_server with a fully mocked engine.
    We patch create_engine before importing the module.
    """
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi[testclient] not installed")

    mock_engine = _make_mock_engine()

    # Patch create_engine so the module-level initialization succeeds
    monkeypatch.setenv("FISH_MODEL_DIR", str(tmp_path))
    with patch("inference_runtime.inference.create_engine", return_value=mock_engine):
        # Force re-import so module-level code re-runs with our mock
        if "inference_runtime.runtime_server" in sys.modules:
            del sys.modules["inference_runtime.runtime_server"]
        import inference_runtime.runtime_server as srv

    return TestClient(srv.app)


class TestRootEndpoint:
    def test_root_returns_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "endpoints" in data


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_health_contains_device(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "device" in data


class TestModelInfoEndpoint:
    def test_model_info(self, client):
        resp = client.get("/model/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "dataset_name" in data or "num_keypoints" in data


class TestInferImageEndpoint:
    def test_infer_image_with_json(self, client, tmp_path):
        """The /infer/image endpoint accepts JSON with image_path."""
        import cv2

        img_path = tmp_path / "test.png"
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(img_path), img)

        resp = client.post("/infer/image", json={"image_path": str(img_path)})
        assert resp.status_code == 200
        data = resp.json()
        assert "keypoints" in data

    def test_infer_image_missing_file(self, client):
        resp = client.post("/infer/image", json={"image_path": "/nonexistent/image.png"})
        assert resp.status_code == 404
