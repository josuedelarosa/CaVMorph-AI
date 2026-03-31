#!/usr/bin/env python3
"""
Fishometrics – Lightweight ONNX Runtime Setup
Replaces the heavy Conda/MMPose setup with a simple pip-based installation.

Steps:
  1. Verify Python is available
  2. Create a virtual environment in app data
  3. Install pip dependencies (onnxruntime, numpy, opencv, fastapi, uvicorn)
  4. Verify model files are present
  5. Quick smoke-test import

Progress is reported as JSON lines on stdout so the Tauri shell can parse them.
"""

import json
import os
import platform
import subprocess
import sys
import venv
from pathlib import Path

# ---------------------------------------------------------------------------
# Packages required by inference_runtime
# ---------------------------------------------------------------------------
REQUIRED_PACKAGES = [
    "onnxruntime>=1.17.0",
    "numpy>=1.24.0,<2.0",
    "opencv-python-headless>=4.8.0",
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "pillow>=9.0.0",
]


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------
def emit(type_: str, step: int = 0, message: str = "", level: str = "info"):
    """Print a JSON line for Tauri to parse."""
    payload = {"type": type_, "step": step, "message": message, "level": level}
    print(json.dumps(payload), flush=True)


def emit_progress(step: int, message: str, level: str = "info"):
    emit("progress", step=step, message=message, level=level)


def emit_complete():
    emit("complete")


def emit_error(message: str):
    emit("error", message=message, level="error")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run(cmd, **kwargs):
    """Run a subprocess, capturing output."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        **kwargs,
    )
    return result


def venv_python(venv_dir: Path) -> Path:
    """Return the python executable inside a venv."""
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def step_check_python():
    """Step 0 – verify the running Python is usable."""
    emit_progress(0, f"Python {platform.python_version()} on {platform.system()}")
    v = sys.version_info
    if v < (3, 9):
        emit_error(f"Python 3.9+ required, found {platform.python_version()}")
        sys.exit(1)
    emit_progress(0, "Python version OK")


def step_create_venv(venv_dir: Path):
    """Step 1 – create a lightweight virtual environment."""
    py = venv_python(venv_dir)
    if py.exists():
        emit_progress(1, "Virtual environment already exists – reusing")
        return
    emit_progress(1, f"Creating virtual environment at {venv_dir}")
    try:
        venv.create(str(venv_dir), with_pip=True, clear=False)
    except Exception as exc:
        emit_error(f"Failed to create venv: {exc}")
        sys.exit(1)
    if not py.exists():
        emit_error(f"venv created but python not found at {py}")
        sys.exit(1)
    emit_progress(1, "Virtual environment created")


def step_install_deps(venv_dir: Path):
    """Step 2 – pip-install required packages into the venv."""
    py = str(venv_python(venv_dir))

    # Upgrade pip first
    emit_progress(2, "Upgrading pip…")
    run([py, "-m", "pip", "install", "--upgrade", "pip"])

    emit_progress(2, "Installing dependencies (this may take a few minutes)…")
    cmd = [py, "-m", "pip", "install", "--upgrade"] + REQUIRED_PACKAGES
    result = run(cmd)
    if result.returncode != 0:
        stderr = result.stderr or result.stdout
        emit_error(f"pip install failed:\n{stderr[-500:]}")
        sys.exit(1)
    emit_progress(2, "Dependencies installed successfully")


def step_verify_model(model_dir: Path):
    """Step 3 – check that model.onnx and model_metadata.json are present."""
    onnx = model_dir / "model.onnx"
    meta = model_dir / "model_metadata.json"

    if not onnx.exists():
        emit_error(f"model.onnx not found at {onnx}")
        sys.exit(1)
    size_mb = onnx.stat().st_size / (1024 * 1024)
    emit_progress(3, f"model.onnx found ({size_mb:.0f} MB)")

    if not meta.exists():
        emit_error(f"model_metadata.json not found at {meta}")
        sys.exit(1)
    emit_progress(3, "Model files verified")


def step_smoke_test(venv_dir: Path):
    """Step 4 – quick import check inside the venv."""
    py = str(venv_python(venv_dir))
    script = (
        "import onnxruntime, numpy, cv2, fastapi, uvicorn, pydantic; "
        "print('OK')"
    )
    result = run([py, "-c", script])
    if result.returncode != 0 or "OK" not in (result.stdout or ""):
        stderr = result.stderr or result.stdout
        emit_error(f"Smoke test failed:\n{stderr[-500:]}")
        sys.exit(1)
    emit_progress(4, "All packages verified")


def step_finalize(app_data: Path):
    """Step 5 – write config.json so the app knows setup is done."""
    config = {
        "setup_complete": True,
        "runtime": "onnx",
        "venv_dir": str(app_data / "venv"),
    }
    config_path = app_data / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    emit_progress(5, "Configuration saved")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--app-data-dir", type=str, default=None)
    parser.add_argument("--model-dir", type=str, default=None)
    parser.add_argument("--backend-dir", type=str, default=None)
    args = parser.parse_args()

    # Resolve paths
    if args.app_data_dir:
        app_data = Path(args.app_data_dir)
    else:
        if platform.system() == "Windows":
            app_data = Path(os.environ.get("APPDATA", Path.home())) / "Fishometrics"
        elif platform.system() == "Darwin":
            app_data = Path.home() / ".fishometrics"
        else:
            app_data = Path.home() / ".local" / "share" / "fishometrics"

    app_data.mkdir(parents=True, exist_ok=True)
    venv_dir = app_data / "venv"

    # Model dir: explicit flag  → app-data/models  → dev repo
    if args.model_dir:
        model_dir = Path(args.model_dir)
    else:
        model_dir = app_data / "models" / "cavfish_v1"
        if not (model_dir / "model.onnx").exists():
            # Try dev repo fallback
            script_dir = Path(__file__).resolve().parent
            dev_model = script_dir.parent / "models" / "cavfish_v1"
            if (dev_model / "model.onnx").exists():
                model_dir = dev_model

    emit_progress(0, "Starting Fishometrics ONNX runtime setup…")

    step_check_python()
    step_create_venv(venv_dir)
    step_install_deps(venv_dir)
    step_verify_model(model_dir)
    step_smoke_test(venv_dir)
    step_finalize(app_data)

    emit_complete()


if __name__ == "__main__":
    main()
