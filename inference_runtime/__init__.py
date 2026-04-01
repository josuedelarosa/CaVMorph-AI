# Inference Runtime
"""
Thin inference runtime for Fishometrics.
No MMPose, no Conda, no training code required.
"""
from .inference import ONNXInferenceEngine, FallbackPyTorchEngine, create_engine
from .types import ModelMetadata, InferenceRequest, InferenceResult

__all__ = [
    "ONNXInferenceEngine",
    "FallbackPyTorchEngine",
    "create_engine",
    "ModelMetadata",
    "InferenceRequest",
    "InferenceResult",
]
