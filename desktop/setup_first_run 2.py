#!/usr/bin/env python3
"""
Fish Morphometrics - First Run Setup Script
This script is executed by the Tauri app on first launch to set up the environment.

It handles:
1. Detecting/installing conda
2. Creating the cavfish310 environment
3. Installing PyTorch, mmpose, and dependencies
4. Downloading model weights
"""

import sys
import os
import json
import subprocess
import platform
import urllib.request
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Callable
import time


# Configuration
ENV_NAME = "cavfish310"
PYTHON_VERSION = "3.10"

# Model hosting - UPDATE THIS with your actual hosting URL
MODEL_WEIGHTS_URL = os.environ.get(
    "FISH_MODEL_URL",
    "https://github.com/josuedelarosa/cavfish-weights/releases/download/v1/weights.pth"
)
MODEL_WEIGHTS_SHA256 = os.environ.get("FISH_MODEL_SHA256", "")  # Optional checksum


class SetupProgress:
    """Handles progress reporting to the Tauri frontend."""
    
    def __init__(self):
        self.current_step = 0
        self.callback: Optional[Callable] = None
    
    def set_callback(self, callback: Callable):
        self.callback = callback
    
    def report(self, step: int, message: str, level: str = "info"):
        """Report progress to stdout in JSON format for Tauri to parse."""
        self.current_step = step
        output = json.dumps({
            "type": "progress",
            "step": step,
            "message": message,
            "level": level
        })
        print(output, flush=True)
    
    def complete(self):
        print(json.dumps({"type": "complete"}), flush=True)
    
    def error(self, message: str):
        print(json.dumps({"type": "error", "message": message}), flush=True)


progress = SetupProgress()


def get_app_data_dir() -> Path:
    """Get the application data directory."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "FishMorph"
    elif platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "FishMorph"
    else:
        return Path.home() / ".local" / "share" / "FishMorph"


def find_conda() -> Optional[Path]:
    """Find conda installation."""
    home = Path.home()
    
    candidates = [
        home / "miniforge3" / "bin" / "conda",
        home / "mambaforge" / "bin" / "conda",
        home / "miniconda3" / "bin" / "conda",
        home / "anaconda3" / "bin" / "conda",
        Path("/opt/homebrew/Caskroom/miniforge/base/bin/conda"),
        Path("/usr/local/Caskroom/miniforge/base/bin/conda"),
    ]
    
    for conda_path in candidates:
        if conda_path.exists():
            return conda_path
    
    # Try PATH
    try:
        result = subprocess.run(["which", "conda"], capture_output=True, text=True)
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except:
        pass
    
    return None


def run_command(cmd: list, env: dict = None, cwd: str = None, timeout: int = 600) -> tuple:
    """Run a command and return (success, output)."""
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=full_env,
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_env_exists(conda_path: Path) -> bool:
    """Check if the conda environment already exists."""
    success, output = run_command([str(conda_path), "env", "list"])
    return success and ENV_NAME in output


def verify_packages(conda_path: Path) -> bool:
    """Verify that all required packages are installed."""
    conda_base = conda_path.parent.parent
    python_path = conda_base / "envs" / ENV_NAME / "bin" / "python"
    
    if not python_path.exists():
        return False
    
    check_script = """
import sys
try:
    import torch
    import mmpose
    import mmengine
    import mmcv
    import mmdet
    import fastapi
    import uvicorn
    import cv2
    print("OK")
except ImportError as e:
    print(f"MISSING: {e}")
    sys.exit(1)
"""
    
    success, output = run_command([str(python_path), "-c", check_script])
    return success and "OK" in output


def verify_module(python_path: Path, module_name: str, version: str = None, retries: int = 2) -> tuple:
    """
    Verify a specific module is installed and optionally check version.
    Returns (success: bool, error_message: str)
    """
    import time
    
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(1)  # Wait 1 second before retry
        
        if version:
            check_script = f"""
import sys
try:
    import {module_name}
    installed_version = {module_name}.__version__
    print(f"{{installed_version}}")
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(1)
except AttributeError:
    print("unknown")
"""
        else:
            check_script = f"""
import sys
try:
    import {module_name}
    print("OK")
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(1)
"""
        
        success, output = run_command([str(python_path), "-c", check_script], timeout=30)
        
        if not success:
            if "IMPORT_ERROR" in output:
                error_msg = output.strip()
                if attempt < retries - 1:
                    continue  # Retry
                return False, error_msg
            return False, f"Verification command failed: {output[:200]}"
        
        if version and success:
            installed = output.strip()
            expected_major = version.split("==")[-1].split(".")[0]
            if installed.startswith(expected_major) or installed == "unknown":
                return True, ""
            return False, f"Version mismatch: expected {version}, got {installed}"
        
        if "OK" in output:
            return True, ""
    
    return False, "Module verification failed after retries"


def ensure_numpy_lt2(conda_path: Path) -> bool:
    """Force NumPy to stay below 2.x using conda then pip to avoid binary ABI issues."""
    conda_base = conda_path.parent.parent
    python_path = conda_base / "envs" / ENV_NAME / "bin" / "python"

    # Remove any existing numpy (from pip) quietly (twice to be sure)
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)

    # Reinstall via conda to lock the ABI-compatible build (force-reinstall)
    success, output = run_command(
        [str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"],
        timeout=240
    )
    if not success:
        progress.report(0, f"Failed to enforce numpy<2 via conda: {output}", "error")
        return False

    # Final verification
    ok, err = verify_module(python_path, "numpy")
    if not ok:
        progress.report(0, f"numpy<2 verification failed: {err}", "error")
        return False
    return True


def step_check_system():
    """Step 1: Check system and find conda."""
    progress.report(0, "Checking system configuration...")
    
    conda_path = find_conda()
    if not conda_path:
        progress.report(0, "Conda not found. Please install Miniforge first.", "error")
        progress.report(0, "Install with: brew install --cask miniforge", "info")
        return None
    
    progress.report(0, f"Found conda at: {conda_path}", "success")
    
    # Check if environment already exists and is valid
    if check_env_exists(conda_path):
        progress.report(0, f"Environment '{ENV_NAME}' exists, verifying...", "info")
        if verify_packages(conda_path):
            progress.report(0, "Environment is ready!", "success")
            return {"conda": conda_path, "skip_install": True}
    
    return {"conda": conda_path, "skip_install": False}


def step_create_env(conda_path: Path):
    """Step 2: Create conda environment."""
    progress.report(1, f"Creating conda environment '{ENV_NAME}'...")
    
    # Remove existing environment if it exists but is broken
    if check_env_exists(conda_path):
        progress.report(1, "Removing existing environment...", "warning")
        run_command([str(conda_path), "env", "remove", "-n", ENV_NAME, "-y"])
    
    # Create new environment with python and pip
    success, output = run_command(
        [str(conda_path), "create", "-n", ENV_NAME, "-c", "conda-forge", 
         f"python={PYTHON_VERSION}", "pip", "-y"],
        timeout=300
    )
    
    if not success:
        progress.report(1, f"Failed to create environment: {output}", "error")
        return False
    
    progress.report(1, "Environment created successfully", "success")
    return True


def step_install_pytorch(conda_path: Path):
    """Step 3: Install PyTorch (via conda, not pip) - EXACT ORDER MATTERS!"""
    progress.report(2, "Installing PyTorch (this may take a few minutes)...")
    
    conda_base = conda_path.parent.parent
    pip_path = conda_base / "envs" / ENV_NAME / "bin" / "pip"
    python_path = conda_base / "envs" / ENV_NAME / "bin" / "python"
    
    # Step 1: Upgrade pip, setuptools, wheel
    progress.report(2, "Upgrading pip, setuptools, wheel...", "info")
    success, output = run_command([str(python_path), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], timeout=120)
    if not success:
        progress.report(2, f"pip upgrade failed: {output}", "warning")
    
    # Step 2: Force uninstall numpy (critical - ignore errors if not present)
    progress.report(2, "Uninstalling any existing numpy...", "info")
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    
    # Step 3: Install numpy<2 via conda (not pip!)
    progress.report(2, "Installing numpy<2 via conda-forge...", "info")
    success, output = run_command(
        [str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2"],
        timeout=180
    )
    if not success:
        progress.report(2, f"numpy installation failed: {output}", "error")
        return False
    
    # Verify numpy installation
    progress.report(2, "Verifying numpy installation...", "info")
    success, error = verify_module(python_path, "numpy")
    if not success:
        progress.report(2, f"numpy verification failed: {error}", "error")
        return False

    
    # Step 4: Install xtcocotools
    progress.report(2, "Installing xtcocotools...", "info")
    success, output = run_command([str(python_path), "-m", "pip", "install", "xtcocotools"], timeout=120)
    if not success:
        progress.report(2, f"xtcocotools installation failed: {output}", "error")
        return False
    
    # Verify xtcocotools installation
    progress.report(2, "Verifying xtcocotools...", "info")
    success, error = verify_module(python_path, "xtcocotools")
    if not success:
        progress.report(2, f"xtcocotools verification failed: {error}", "error")
        return False
    
    # Step 5: Install PyTorch + torchvision + cpuonly via conda
    progress.report(2, "Installing PyTorch from conda-pytorch...", "info")
    success, output = run_command(
        [str(conda_path), "install", "-n", ENV_NAME, "-c", "pytorch", "-y",
         "pytorch", "torchvision", "cpuonly"],
        timeout=600
    )
    
    if not success:
        progress.report(2, f"PyTorch installation failed: {output}", "error")
        return False
    
    # Verify PyTorch installation
    progress.report(2, "Verifying PyTorch installation...", "info")
    success, error = verify_module(python_path, "torch")
    if not success:
        progress.report(2, f"PyTorch verification failed: {error}", "error")
        return False
    success, error = verify_module(python_path, "torchvision")
    if not success:
        progress.report(2, f"torchvision verification failed: {error}", "error")
        return False
    
    progress.report(2, "PyTorch installed and verified successfully", "success")
    return True


def step_install_mm_packages(conda_path: Path):
    """Step 4: Install mmpose and related packages - EXACT ORDER MATTERS!"""
    progress.report(3, "Installing mmpose ecosystem (this may take several minutes)...")
    
    conda_base = conda_path.parent.parent
    pip_path = conda_base / "envs" / ENV_NAME / "bin" / "pip"
    python_path = conda_base / "envs" / ENV_NAME / "bin" / "python"
    
    # Define source directory for git clones (persistent)
    src_dir = conda_base / "envs" / ENV_NAME / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 2: Install OpenMIM
    progress.report(3, "Installing OpenMIM...", "info")
    success, output = run_command([str(python_path), "-m", "pip", "install", "-U", "openmim"], timeout=180)
    if not success:
        progress.report(3, f"OpenMIM installation failed: {output}", "error")
        return False

    # Verify OpenMIM installation (module is 'mim')
    progress.report(3, "Verifying OpenMIM (mim module)...", "info")
    success, error = verify_module(python_path, "mim")
    if not success:
        progress.report(3, f"OpenMIM verification failed: {error}", "error")
        return False

    mim_path = conda_base / "envs" / ENV_NAME / "bin" / "mim"

    # Step 3: Install fsspec
    progress.report(3, "Installing fsspec...", "info")
    success, output = run_command([str(python_path), "-m", "pip", "install", "fsspec"], timeout=180)
    if not success:
        progress.report(3, f"fsspec installation failed: {output}", "error")
        return False
    
    # Verify fsspec installation
    progress.report(3, "Verifying fsspec...", "info")
    success, error = verify_module(python_path, "fsspec")
    if not success:
        progress.report(3, f"fsspec verification failed: {error}", "error")
        return False
    
    # Step 3: Install exact mmengine version
    progress.report(3, "Installing mmengine==0.10.7...", "info")
    success, output = run_command([str(mim_path), "install", "mmengine==0.10.7"], timeout=300)
    if not success:
        progress.report(3, f"mmengine installation failed: {output}", "error")
        return False
    
    # Verify mmengine installation
    progress.report(3, "Verifying mmengine installation...", "info")
    success, error = verify_module(python_path, "mmengine", "0.10.7")
    if not success:
        progress.report(3, f"mmengine verification failed: {error}", "error")
        return False
    
    # Step 4: Install exact mmcv version
    progress.report(3, "Installing mmcv==2.1.0...", "info")
    success, output = run_command([str(mim_path), "install", "mmcv==2.1.0"], timeout=900)
    if not success:
        progress.report(3, f"mmcv installation failed: {output}", "error")
        return False
    
    # Verify mmcv installation and EXTENSIONS
    progress.report(3, "Verifying mmcv installation and extensions...", "info")
    mmcv_check = """
import sys
import json

try:
    import mmcv
    print(json.dumps({"mmcv_version": mmcv.__version__}))
    from mmcv.ops import nms
    print("OPS_OK")
except ImportError as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
"""
    success, output = run_command([str(python_path), "-c", mmcv_check], timeout=120)
    if not success or "OPS_OK" not in output:
        progress.report(3, f"mmcv verification failed (missing extensions or numpy drift?): {output}", "error")
        return False
    progress.report(3, "mmcv extensions verified.", "success")
    
    # Step 5: Install chumpy via conda-forge (after PyTorch and mmcv - IMPORTANT!)
    progress.report(3, "Installing chumpy via conda-forge...", "info")
    success, output = run_command(
        [str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "chumpy"],
        timeout=120
    )
    if not success:
        progress.report(3, f"chumpy installation failed: {output}", "warning")
    
    # Step 6: Clone and install mmpose from git to PERSISTENT src location
    progress.report(3, "Installing mmpose from git source...", "info")
    
    # Use persistent source directory
    mmpose_dir = src_dir / "mmpose"
    if mmpose_dir.exists():
        progress.report(3, "Cleaning existing mmpose source...", "info")
        shutil.rmtree(mmpose_dir)
    
    progress.report(3, f"Cloning mmpose to {mmpose_dir}...", "info")
    success, output = run_command(
        ["git", "clone", "https://github.com/open-mmlab/mmpose.git", str(mmpose_dir)],
        timeout=300
    )
    if not success:
        progress.report(3, f"Failed to clone mmpose: {output}", "error")
        return False
    
    # Install mmpose requirements
    progress.report(3, "Installing mmpose requirements...", "info")
    success, output = run_command(
        [str(python_path), "-m", "pip", "install", "-r", str(mmpose_dir / "requirements.txt")],
        timeout=300
    )
    if not success:
        progress.report(3, f"Failed to install mmpose requirements: {output}", "warning")
        # Continue anyway
    
    # Install mmpose in editable mode (-e)
    progress.report(3, "Installing mmpose package in editable mode...", "info")
    success, output = run_command(
        [str(python_path), "-m", "pip", "install", "-e", str(mmpose_dir)],
        cwd=str(mmpose_dir),
        timeout=300
    )
    if not success:
        progress.report(3, f"mmpose installation failed: {output}", "error")
        return False
    
    # Verify mmpose installation
    progress.report(3, "Verifying mmpose installation...", "info")
    success, error = verify_module(python_path, "mmpose")
    if not success:
        progress.report(3, f"mmpose verification failed: {error}", "error")
        return False
    
    # Step 7: Install mmpretrain
    progress.report(3, "Installing mmpretrain==1.2.0...", "info")
    success, output = run_command([str(mim_path), "install", "mmpretrain==1.2.0"], timeout=300)
    if not success:
        progress.report(3, f"mmpretrain installation failed: {output}", "warning")
    else:
        success, error = verify_module(python_path, "mmpretrain", "1.2.0")
        if not success:
            progress.report(3, f"mmpretrain verification failed: {error}", "warning")

    # Step 8: Install mmdet (MMDetection) - AFTER mmpose to ensure compatibility
    progress.report(3, "Installing mmdet==3.3.0...", "info")
    success, output = run_command([str(mim_path), "install", "mmdet==3.3.0"], timeout=600)
    if not success:
        progress.report(3, f"mmdet installation failed: {output}", "error")
        return False
    
    # Verify mmdet installation
    progress.report(3, "Verifying mmdet installation...", "info")
    success, error = verify_module(python_path, "mmdet", "3.3.0")
    if not success:
        progress.report(3, f"mmdet verification failed: {error}", "error")
        return False
    
    # FINAL STEP: Force numpy<2 via conda after all MM packages are installed
    progress.report(3, "Final enforcement: forcing numpy<2 via conda...", "info")
    if not ensure_numpy_lt2(conda_path):
        progress.report(3, "Failed to force numpy<2 after MM package installation", "error")
        return False
    
    progress.report(3, "mmpose ecosystem installed and verified successfully", "success")
    return True


def step_install_dependencies(conda_path: Path, backend_dir: Path):
    """Step 5: Install other dependencies."""
    progress.report(4, "Installing additional dependencies...")
    
    conda_base = conda_path.parent.parent
    pip_path = conda_base / "envs" / ENV_NAME / "bin" / "pip"
    
    deps = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "opencv-python==4.8.1.78",
        "Pillow",
    ]
    
    for dep in deps:
        progress.report(4, f"Installing {dep}...", "info")
        success, output = run_command([str(pip_path), "install", dep], timeout=180)
        if not success:
            progress.report(4, f"Failed to install {dep}: {output}", "error")
            return False
    
    # Install the backend package if pyproject.toml exists
    pyproject = backend_dir / "backend" / "pyproject.toml"
    if pyproject.exists():
        progress.report(4, "Installing cavfish backend package...", "info")
        success, output = run_command(
            [str(pip_path), "install", "-e", str(backend_dir / "backend")],
            timeout=120
        )
        if not success:
            progress.report(4, f"Backend package install failed (non-critical): {output}", "warning")
    
    progress.report(4, "Dependencies installed successfully", "success")
    return True


def step_download_model(app_data_dir: Path, bundled_model: Optional[Path] = None):
    """Step 6: Download or copy model weights."""
    progress.report(5, "Setting up model weights...")
    
    models_dir = app_data_dir / "models" / "cavfish_v1"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    weights_path = models_dir / "weights.pth"
    
    # Check if model already exists
    if weights_path.exists():
        progress.report(5, "Model weights already present", "success")
        return True
    
    # Check for bundled model in resources
    if bundled_model and bundled_model.exists():
        progress.report(5, "Copying bundled model weights...", "info")
        try:
            shutil.copy2(bundled_model, weights_path)
            progress.report(5, "Model weights copied successfully", "success")
            return True
        except Exception as e:
            progress.report(5, f"Failed to copy model: {e}", "error")
            return False
    
    # Download from URL if configured
    if MODEL_WEIGHTS_URL and "YOUR_USERNAME" not in MODEL_WEIGHTS_URL:
        progress.report(5, f"Downloading model weights (~1GB)...", "info")
        try:
            last_percent = -1  # Track last reported percentage
            
            def report_progress(block_num, block_size, total_size):
                nonlocal last_percent
                if total_size > 0:
                    percent = min(100, block_num * block_size * 100 // total_size)
                    # Only report when percentage actually changes
                    if percent != last_percent:
                        last_percent = percent
                        progress.report(5, f"Downloading: {percent}%", "info")
            
            urllib.request.urlretrieve(MODEL_WEIGHTS_URL, weights_path, report_progress)
            
            # Verify checksum if provided
            if MODEL_WEIGHTS_SHA256:
                progress.report(5, "Verifying download...", "info")
                sha256_hash = hashlib.sha256()
                with open(weights_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256_hash.update(chunk)
                if sha256_hash.hexdigest().lower() != MODEL_WEIGHTS_SHA256.lower():
                    progress.report(5, "Checksum verification failed!", "error")
                    weights_path.unlink()
                    return False
            
            progress.report(5, "Model downloaded successfully", "success")
            return True
        except Exception as e:
            progress.report(5, f"Download failed: {e}", "error")
            return False
    
    progress.report(5, "No model source configured - please add weights manually", "warning")
    progress.report(5, f"Place weights.pth in: {models_dir}", "info")
    return True  # Don't fail setup for missing model


def step_finalize(conda_path: Path, app_data_dir: Path, backend_dir: Path):
    """Step 7: Verify installation and save config."""
    progress.report(6, "Verifying installation...")
    
    # Verify packages
    if not verify_packages(conda_path):
        progress.report(6, "Package verification failed", "error")
        return False
    
    # Copy backend source to app data
    backend_dest = app_data_dir / "backend"
    
    # Find the backend source - could be:
    # 1. backend_dir/backend (dev mode, running from project root)
    # 2. backend_dir (production, Resources/backend/ already contains api/, cavfish/)
    # 3. backend_dir/_up_/_up_/backend (Tauri resource bundling with ../../ paths)
    backend_src = None
    
    # Check various possible locations
    possible_paths = [
        backend_dir / "backend",  # dev mode
        backend_dir,  # direct
        backend_dir / "_up_" / "_up_" / "backend",  # Tauri ../../ resource path
        backend_dir / "_up_" / "backend",  # Tauri ../ resource path
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "api").exists():
            backend_src = path
            progress.report(6, f"Found backend at: {backend_src}", "info")
            break
    
    if not backend_src:
        # List what's in backend_dir for debugging
        progress.report(6, f"Searching for backend in: {backend_dir}", "info")
        try:
            contents = list(backend_dir.iterdir())[:10]
            progress.report(6, f"Directory contains: {[p.name for p in contents]}", "info")
        except Exception as e:
            progress.report(6, f"Could not list directory: {e}", "warning")
    
    if backend_src and backend_src.exists():
        progress.report(6, "Copying backend files...", "info")
        try:
            if backend_dest.exists():
                shutil.rmtree(backend_dest)
            shutil.copytree(
                backend_src,
                backend_dest,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git', 'tmp', 'target')
            )
            progress.report(6, f"Backend copied to: {backend_dest}", "success")
        except Exception as e:
            progress.report(6, f"Failed to copy backend: {e}", "error")
            return False
    else:
        progress.report(6, f"Backend source not found in {backend_dir}", "error")
        progress.report(6, f"Checked: {backend_dir}/backend/api, {backend_dir}/api", "info")
        return False
    
    # Copy model config files
    models_src = backend_dir / "models" / "cavfish_v1"
    models_dest = app_data_dir / "models" / "cavfish_v1"
    if models_src.exists():
        for config_file in ["meta.json", "config.py", "config_infer.py"]:
            src = models_src / config_file
            dest = models_dest / config_file
            if src.exists() and not dest.exists():
                try:
                    shutil.copy2(src, dest)
                except:
                    pass
    
    # Save configuration
    config = {
        "setup_complete": True,
        "conda_env": ENV_NAME,
        "conda_path": str(conda_path),
        "backend_dir": str(backend_dest),
        "models_dir": str(app_data_dir / "models"),
        "version": "0.1.0"
    }
    
    config_file = app_data_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    progress.report(6, "Setup verified successfully", "success")
    return True


def main():
    """Main setup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fish Morphometrics Setup")
    parser.add_argument("--backend-dir", type=str, help="Path to backend source")
    parser.add_argument("--bundled-model", type=str, help="Path to bundled model weights")
    args = parser.parse_args()
    
    app_data_dir = get_app_data_dir()
    app_data_dir.mkdir(parents=True, exist_ok=True)
    
    backend_dir = Path(args.backend_dir) if args.backend_dir else Path.cwd()
    bundled_model = Path(args.bundled_model) if args.bundled_model else None
    
    try:
        # Step 1: Check system
        result = step_check_system()
        if result is None:
            progress.error("System check failed - conda not found")
            sys.exit(1)
        
        conda_path = result["conda"]
        
        # Skip installation if environment is ready
        if result.get("skip_install"):
            progress.report(1, "Skipping installation (environment ready)", "success")
            progress.report(2, "Skipping (already installed)", "success")
            progress.report(3, "Skipping (already installed)", "success")
            progress.report(4, "Skipping (already installed)", "success")
        else:
            # Step 2: Create environment
            if not step_create_env(conda_path):
                progress.error("Failed to create conda environment")
                sys.exit(1)
            
            # Step 3: Install PyTorch
            if not step_install_pytorch(conda_path):
                progress.error("Failed to install PyTorch")
                sys.exit(1)
            
            # Step 4: Install MM packages
            if not step_install_mm_packages(conda_path):
                progress.error("Failed to install mmpose packages")
                sys.exit(1)
            
            # Step 5: Install dependencies
            if not step_install_dependencies(conda_path, backend_dir):
                progress.error("Failed to install dependencies")
                sys.exit(1)
        
        # Step 6: Download/setup model
        if not step_download_model(app_data_dir, bundled_model):
            progress.error("Failed to set up model weights")
            sys.exit(1)
        
        # Step 7: Finalize
        if not step_finalize(conda_path, app_data_dir, backend_dir):
            progress.error("Setup verification failed")
            sys.exit(1)
        
        progress.complete()
        
    except Exception as e:
        progress.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
