#!/usr/bin/env python3
"""
PhenoAI - First Run Setup Script
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
        # Use hidden folder to avoid spaces in path (Miniforge installer issue)
        return Path.home() / ".phenoai"
    elif platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "PhenoAI"
    else:
        return Path.home() / ".local" / "share" / "phenoai"


def get_app_conda_dir() -> Path:
    """Get the app-managed conda installation directory."""
    return get_app_data_dir() / "conda"


def conda_executable_from_prefix(prefix: Path) -> Path:
    """Return conda executable path for a conda install prefix."""
    if platform.system() == "Windows":
        return prefix / "Scripts" / "conda.exe"
    return prefix / "bin" / "conda"


def python_candidates_from_env(env_path: Path) -> list[Path]:
    """Return possible Python executable paths for a conda env."""
    if platform.system() == "Windows":
        return [env_path / "python.exe", env_path / "Scripts" / "python.exe"]
    return [env_path / "bin" / "python"]


def python_executable_from_env(env_path: Path) -> Path:
    """Return preferred Python executable path from a conda env."""
    for candidate in python_candidates_from_env(env_path):
        if candidate.exists():
            return candidate
    return python_candidates_from_env(env_path)[0]


def pip_executable_from_env(env_path: Path) -> Path:
    """Return preferred pip executable path from a conda env."""
    if platform.system() == "Windows":
        return env_path / "Scripts" / "pip.exe"
    return env_path / "bin" / "pip"


def first_path_line(text: str) -> str:
    """Return first non-empty line from command output."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_git_available() -> bool:
    """Check if git is available in PATH."""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def install_miniforge(target_dir: Path) -> bool:
    """Download and install Miniforge to the target directory."""
    progress.report(0, "Downloading Miniforge installer...", "info")
    
    # Determine platform and architecture
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin":
        if machine == "arm64":
            installer_url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
        else:
            installer_url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
    elif system == "Linux":
        if machine == "aarch64":
            installer_url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh"
        else:
            installer_url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
    elif system == "Windows":
        installer_url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
    else:
        progress.report(0, f"Unsupported platform: {system}", "error")
        return False
    
    # Download installer
    installer_path = target_dir.parent / f"miniforge_installer{'.exe' if system == 'Windows' else '.sh'}"
    try:
        progress.report(0, f"Downloading from {installer_url}...", "info")
        urllib.request.urlretrieve(installer_url, installer_path)
    except Exception as e:
        progress.report(0, f"Download failed: {e}", "error")
        return False
    
    # Install Miniforge
    progress.report(0, "Installing Miniforge (this may take a few minutes)...", "info")
    progress.report(0, f"Installation path: {target_dir}", "info")
    
    # Ensure target directory parent exists
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if system == "Windows":
            # Windows installer
            success, output = run_command(
                [str(installer_path), "/InstallationType=JustMe", "/RegisterPython=0", 
                 "/S", f"/D={target_dir}"],
                timeout=600
            )
        else:
            # Unix installer - use absolute paths
            os.chmod(installer_path, 0o755)
            # Miniforge installer doesn't handle spaces well, but our new path has no spaces
            success, output = run_command(
                ["bash", str(installer_path.resolve()), "-b", "-p", str(target_dir.resolve())],
                timeout=600
            )
        
        if not success:
            progress.report(0, f"Installation failed: {output}", "error")
            return False
        
        # Cleanup installer
        installer_path.unlink()
        
        progress.report(0, "Miniforge installed successfully", "success")
        return True
        
    except Exception as e:
        progress.report(0, f"Installation error: {e}", "error")
        return False


def find_conda() -> Optional[Path]:
    """Find conda installation - prioritize app-managed conda."""
    # First check app-managed conda
    app_conda = conda_executable_from_prefix(get_app_conda_dir())
    if app_conda.exists():
        return app_conda
    
    # Fallback to system conda
    home = Path.home()
    
    candidates = [
        conda_executable_from_prefix(home / "miniforge3"),
        conda_executable_from_prefix(home / "mambaforge"),
        conda_executable_from_prefix(home / "miniconda3"),
        conda_executable_from_prefix(home / "anaconda3"),
    ]

    if platform.system() == "Windows":
        candidates.extend([
            Path("C:/ProgramData/miniforge3/Scripts/conda.exe"),
            Path("C:/ProgramData/mambaforge/Scripts/conda.exe"),
            Path("C:/ProgramData/miniconda3/Scripts/conda.exe"),
            Path("C:/ProgramData/Anaconda3/Scripts/conda.exe"),
        ])
    else:
        candidates.extend([
            Path("/opt/homebrew/Caskroom/miniforge/base/bin/conda"),
            Path("/usr/local/Caskroom/miniforge/base/bin/conda"),
        ])
    
    for conda_path in candidates:
        if conda_path.exists():
            return conda_path
    
    # Try PATH
    try:
        lookup = "where" if platform.system() == "Windows" else "which"
        result = subprocess.run([lookup, "conda"], capture_output=True, text=True)
        if result.returncode == 0:
            first = first_path_line(result.stdout)
            if first:
                return Path(first)
    except Exception:
        pass
    
    return None


def run_command(cmd: list, env: dict = None, cwd: str = None, timeout: int = 600) -> tuple:
    """Run a command and return (success, output)."""
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        creationflags = 0
        if platform.system() == "Windows":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=full_env,
            cwd=cwd,
            timeout=timeout,
            creationflags=creationflags,
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
    env_path = get_env_path(conda_path)
    if not env_path:
        progress.report(0, "Could not find environment path", "error")
        return False
    
    python_path = python_executable_from_env(env_path)
    
    if not python_path.exists():
        progress.report(0, f"Python not found at: {python_path}", "error")
        return False
    
    progress.report(0, "Checking installed packages...", "info")
    
    check_script = """
import sys
packages_ok = []
packages_missing = []

for pkg in ['torch', 'mmpose', 'mmengine', 'mmcv', 'mmdet', 'fastapi', 'uvicorn', 'cv2']:
    try:
        __import__(pkg)
        packages_ok.append(pkg)
    except ImportError as e:
        packages_missing.append(f"{pkg}: {e}")

if packages_missing:
    print(f"MISSING: {', '.join(packages_missing)}")
    sys.exit(1)
else:
    print(f"OK: All packages installed ({', '.join(packages_ok)})")
"""
    
    success, output = run_command([str(python_path), "-c", check_script])
    
    if success and "OK" in output:
        progress.report(0, "✓ All packages verified", "success")
        return True
    else:
        progress.report(0, f"Package check failed: {output}", "error")
        return False


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


def check_numpy_version(python_path: Path) -> str:
    """Check current numpy version."""
    check_script = "import numpy; print(numpy.__version__)"
    success, output = run_command([str(python_path), "-c", check_script], timeout=30)
    if success:
        return output.strip().split('\n')[-1]
    return "unknown"

def ensure_numpy_lt2(conda_path: Path) -> bool:
    """Force NumPy to stay below 2.x using conda then pip to avoid binary ABI issues."""
    env_path = get_env_path(conda_path)
    if not env_path:
        return False
    
    python_path = python_executable_from_env(env_path)
    
    current_version = check_numpy_version(python_path)
    progress.report(0, f"Current NumPy version: {current_version}", "info")

    # Remove any existing numpy (from pip) quietly (twice to be sure)
    progress.report(0, "Removing pip-installed numpy...", "info")
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)

    # Reinstall via conda to lock the ABI-compatible build (force-reinstall)
    progress.report(0, "Force-reinstalling numpy<2 via conda-forge...", "info")
    success, output = run_command(
        [str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"],
        timeout=240
    )
    if not success:
        progress.report(0, f"Failed to enforce numpy<2 via conda: {output}", "error")
        return False

    # Final verification
    new_version = check_numpy_version(python_path)
    progress.report(0, f"NumPy after reinstall: {new_version}", "info")
    
    if new_version.startswith('2.'):
        progress.report(0, f"ERROR: NumPy is still 2.x ({new_version}) after force reinstall", "error")
        return False
    
    ok, err = verify_module(python_path, "numpy")
    if not ok:
        progress.report(0, f"numpy<2 verification failed: {err}", "error")
        return False
    return True


def step_check_system():
    """Step 1: Check system and find/install conda."""
    progress.report(0, "Checking system configuration...")
    
    # Check if app-managed conda exists
    app_conda_dir = get_app_conda_dir()
    conda_path = find_conda()
    
    if not conda_path:
        # No conda found - install app-managed Miniforge
        progress.report(0, "Conda not found. Installing app-managed Miniforge...", "info")
        app_conda_dir.parent.mkdir(parents=True, exist_ok=True)
        
        if not install_miniforge(app_conda_dir):
            progress.report(0, "Failed to install Miniforge", "error")
            return None
        
        conda_path = conda_executable_from_prefix(app_conda_dir)
        if not conda_path.exists():
            progress.report(0, "Miniforge installed but conda not found", "error")
            return None
    
    progress.report(0, f"Found conda at: {conda_path}", "success")
    
    # Check if environment already exists and is valid
    if check_env_exists(conda_path):
        progress.report(0, f"Environment '{ENV_NAME}' exists, verifying...", "info")
        if verify_packages(conda_path):
            progress.report(0, "Environment is ready!", "success")
            return {"conda": conda_path, "skip_install": True, "env_exists": True, "env_ready": True}
        
        # Environment exists but is broken - remove it and start fresh
        progress.report(0, "Environment exists but required packages are missing.", "warning")
        progress.report(0, "Removing broken environment...", "info")
        
        # Get the actual path to remove it
        env_path = get_env_path(conda_path)
        if env_path:
            success, output = run_command([str(conda_path), "env", "remove", "-p", str(env_path), "-y"], timeout=120)
        else:
            # Fallback to name if path not found
            success, output = run_command([str(conda_path), "env", "remove", "-n", ENV_NAME, "-y"], timeout=120)
        
        if not success:
            progress.report(0, f"Failed to remove broken environment: {output}", "error")
            return None
        progress.report(0, "Broken environment removed. Will create fresh environment.", "success")
    
    return {"conda": conda_path, "skip_install": False, "env_exists": False, "env_ready": False}


def step_create_env(conda_path: Path):
    """Step 2: Create conda environment."""
    progress.report(1, f"Creating conda environment '{ENV_NAME}'...")
    
    # Accept conda TOS if needed (for newer conda versions)
    progress.report(1, "Accepting conda Terms of Service...", "info")
    # These commands may fail on older conda versions, but that's ok - we ignore the error
    run_command([str(conda_path), "config", "--set", "channel_priority", "flexible"], timeout=30)
    run_command([str(conda_path), "config", "--set", "auto_activate_base", "false"], timeout=30)
    
    # Check one more time in case something changed
    if check_env_exists(conda_path):
        progress.report(1, f"Environment '{ENV_NAME}' still exists. Removing it...", "warning")
        env_path = get_env_path(conda_path)
        if env_path:
            run_command([str(conda_path), "env", "remove", "-p", str(env_path), "-y"], timeout=120)
        else:
            run_command([str(conda_path), "env", "remove", "-n", ENV_NAME, "-y"], timeout=120)
    
    # Create environment using -n flag (let conda manage the path)
    # Use --override-channels and -c conda-forge to avoid Anaconda TOS issues
    success, output = run_command(
        [str(conda_path), "create", "-n", ENV_NAME, f"python={PYTHON_VERSION}", "pip", "-y", "--override-channels", "-c", "conda-forge"],
        timeout=300
    )
    
    if not success:
        progress.report(1, f"Failed to create environment: {output}", "error")
        return False
    
    progress.report(1, "Environment created successfully", "success")
    return True


def get_env_path(conda_path: Path) -> Optional[Path]:
    """Get the actual path where conda created the environment.
    Checks both conda env list output and common fallback locations."""
    
    # First, try to parse conda env list
    success, output = run_command([str(conda_path), "env", "list"], timeout=30)
    if success:
        # Parse conda env list output to find the path
        for line in output.split('\n'):
            if ENV_NAME in line and not line.strip().startswith('#'):
                # Format: "envname    *  /path/to/env" or "envname       /path/to/env"
                parts = line.split()
                # Find the path (last part that looks like a path)
                for part in reversed(parts):
                    if ('/' in part or '\\' in part) and ENV_NAME in part:
                        env_path = Path(part)
                        if env_path.exists():
                            return env_path
    
    # Fallback: check common conda environment locations
    home = Path.home()
    conda_base = conda_path.parent.parent
    app_conda_dir = get_app_conda_dir()
    
    candidates = [
        app_conda_dir / "envs" / ENV_NAME,              # App-managed conda
        home / ".conda" / "envs" / ENV_NAME,            # User conda envs
        conda_base / "envs" / ENV_NAME,                 # Conda base envs
        home / "miniforge3" / "envs" / ENV_NAME,        # Miniforge
        home / "mambaforge" / "envs" / ENV_NAME,        # Mambaforge
        home / "miniconda3" / "envs" / ENV_NAME,        # Miniconda
        home / "anaconda3" / "envs" / ENV_NAME,         # Anaconda
    ]
    
    for candidate in candidates:
        if candidate.exists() and python_executable_from_env(candidate).exists():
            return candidate
    
    return None


def step_install_pytorch(conda_path: Path):
    """Step 3: Install ALL packages following EXACT command sequence - NO intermediate validations."""
    progress.report(2, "Installing all packages (this will take 15-30 minutes)...")
    
    # Get the actual environment path
    env_path = get_env_path(conda_path)
    if not env_path:
        progress.report(2, "Failed to locate environment path", "error")
        return False
    
    python_path = python_executable_from_env(env_path)
    
    if not python_path.exists():
        progress.report(2, f"Python not found at {python_path}", "error")
        return False

    if not check_git_available():
        progress.report(2, "Git is required but was not found in PATH.", "error")
        progress.report(2, "Install Git for Windows and relaunch setup.", "error")
        return False
    
    # Define CaVFish directory - use app data dir so it works on any machine
    app_data = get_app_data_dir()
    cavfish_dir = app_data / "CaVFish"
    
    # Step 1: python -m pip install -U pip setuptools wheel
    progress.report(2, "Upgrading pip, setuptools, wheel...", "info")
    run_command([str(python_path), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], timeout=120)
    
    # Step 2: python -m pip uninstall -y numpy || true
    progress.report(2, "Uninstalling numpy...", "info")
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    
    # Step 3: conda install -c conda-forge -y "numpy<2"
    progress.report(2, "Installing numpy<2...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2"], timeout=180)
    
    # Step 4: python -m pip install xtcocotools
    progress.report(2, "Installing xtcocotools...", "info")
    run_command([str(python_path), "-m", "pip", "install", "xtcocotools"], timeout=120)
    
    # Step 5: conda install pytorch torchvision cpuonly -c pytorch -y
    progress.report(2, "Installing PyTorch...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "pytorch", "torchvision", "cpuonly", "-c", "pytorch", "-y"], timeout=600)
    
    # Step 6: python -m pip install -U openmim
    progress.report(2, "Installing OpenMIM...", "info")
    run_command([str(python_path), "-m", "pip", "install", "-U", "openmim"], timeout=180)
    
    # Step 7: python -m pip install fsspec
    progress.report(2, "Installing fsspec...", "info")
    run_command([str(python_path), "-m", "pip", "install", "fsspec"], timeout=180)
    
    # Step 8: mim install "mmengine==0.10.7"
    progress.report(2, "Installing mmengine==0.10.7...", "info")
    run_command([str(python_path), "-m", "mim", "install", "mmengine==0.10.7", "--no-build-isolation"], timeout=300)
    
    # Step 9: mim install "mmcv==2.1.0"
    progress.report(2, "Installing mmcv==2.1.0...", "info")
    run_command([str(python_path), "-m", "mim", "install", "mmcv==2.1.0", "--no-build-isolation"], timeout=900)
    # Re-lock numpy<2: mim build process can pull in numpy>=2
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"], timeout=180)
    
    # Step 10: conda install -c conda-forge -y chumpy
    progress.report(2, "Installing chumpy...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "chumpy"], timeout=120)
    
    # Step 11: git clone https://github.com/josuedelarosa/CaVFish.git
    progress.report(2, "Cloning CaVFish repository...", "info")
    cavfish_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove old clone if exists to ensure fresh install
    if cavfish_dir.exists():
        import shutil
        shutil.rmtree(cavfish_dir)
    
    success, output = run_command(["git", "clone", "https://github.com/josuedelarosa/CaVFish.git", str(cavfish_dir)], timeout=300)
    if not success:
        progress.report(2, f"Failed to clone CaVFish: {output}", "error")
        return False
    
    if not cavfish_dir.exists():
        progress.report(2, "CaVFish directory not created after clone", "error")
        return False
    
    progress.report(2, f"✓ CaVFish cloned to {cavfish_dir}", "success")
    
    # Step 12: cd CaVFish (handled via cwd parameter below)
    # Step 13: git checkout f050defcddcaed1699c1fcaf2711e59da5ab25a7
    progress.report(2, "Checking out specific commit...", "info")
    success, output = run_command(["git", "checkout", "f050defcddcaed1699c1fcaf2711e59da5ab25a7"], cwd=str(cavfish_dir), timeout=60)
    if not success:
        progress.report(2, f"Failed to checkout commit: {output}", "error")
        return False
    
    # Step 14: python -m pip install -r requirements.txt (THIS INSTALLS MMPOSE!)
    progress.report(2, "Installing CaVFish requirements (includes mmpose)...", "info")
    req_file = cavfish_dir / "requirements.txt"
    if not req_file.exists():
        progress.report(2, f"requirements.txt not found at {req_file}", "error")
        return False
    
    success, output = run_command([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"], cwd=str(cavfish_dir), timeout=600)
    if not success:
        progress.report(2, f"Failed to install requirements: {output}", "error")
        return False
    progress.report(2, "✓ CaVFish requirements installed", "success")
    
    # Step 15: python -m pip install . (NOT -e, regular install for portability)
    progress.report(2, "Installing CaVFish package...", "info")
    success, output = run_command([str(python_path), "-m", "pip", "install", "."], cwd=str(cavfish_dir), timeout=300)
    if not success:
        progress.report(2, f"Failed to install CaVFish: {output}", "error")
        return False
    progress.report(2, "✓ CaVFish installed", "success")
    
    # Step 16: mim install "mmpretrain==1.2.0"
    progress.report(2, "Installing mmpretrain==1.2.0...", "info")
    run_command([str(python_path), "-m", "mim", "install", "mmpretrain==1.2.0", "--no-build-isolation"], timeout=300)
    
    # Step 17: mim install 'mmdet==3.3.0'
    progress.report(2, "Installing mmdet==3.3.0...", "info")
    run_command([str(python_path), "-m", "mim", "install", "mmdet==3.3.0", "--no-build-isolation"], timeout=600)
    
    # Note: mmpose is installed via CaVFish requirements.txt (Step 14)
    
    # Step 18: python -m pip uninstall -y numpy
    progress.report(2, "Uninstalling numpy (first reinstall)...", "info")
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    
    # Step 19: conda install -c conda-forge -y "numpy<2" --force-reinstall
    progress.report(2, "Force reinstalling numpy<2...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"], timeout=180)
    
    # Step 20: conda install -c pytorch -y pytorch torchvision cpuonly --force-reinstall
    progress.report(2, "Force reinstalling PyTorch...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "pytorch", "-y", "pytorch", "torchvision", "cpuonly", "--force-reinstall"], timeout=600)
    
    # Step 21-22: Re-lock numpy<2 (pytorch force-reinstall may have pulled in numpy>=2)
    progress.report(2, "Uninstalling numpy (post-pytorch lock)...", "info")
    run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
    progress.report(2, "Force reinstalling numpy<2 (final lock)...", "info")
    run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"], timeout=180)
    
    # Step 23: Verify mmcv - only reinstall if broken (prior mim install may have already succeeded)
    progress.report(2, "Checking mmcv...", "info")
    verify_ok, verify_out = run_command([str(python_path), "-c", "import mmcv; print('mmcv OK:', mmcv.__version__)"])
    if not verify_ok or "mmcv OK" not in verify_out:
        progress.report(2, "mmcv not importable, attempting mim install...", "warning")
        run_command([str(python_path), "-m", "pip", "uninstall", "-y", "mmcv", "mmcv-lite", "mmcv-full"], timeout=60)
        run_command([str(python_path), "-m", "mim", "install", "mmcv==2.1.0", "--no-build-isolation"], timeout=900)
        # Re-lock numpy<2 after mim (mim build can pull in numpy>=2)
        run_command([str(python_path), "-m", "pip", "uninstall", "-y", "numpy"], timeout=60)
        run_command([str(conda_path), "install", "-n", ENV_NAME, "-c", "conda-forge", "-y", "numpy<2", "--force-reinstall"], timeout=180)
        verify_ok, verify_out = run_command([str(python_path), "-c", "import mmcv; print('mmcv OK:', mmcv.__version__)"])
        if not verify_ok or "mmcv OK" not in verify_out:
            progress.report(2, "mim failed, trying pip fallback...", "warning")
            run_command([str(python_path), "-m", "pip", "uninstall", "-y", "mmcv", "mmcv-lite", "mmcv-full"], timeout=60)
            pip_ok, pip_out = run_command([str(python_path), "-m", "pip", "install", "mmcv==2.1.0", "--no-build-isolation"], timeout=600)
            progress.report(2, f"pip output: {pip_out[:500]}", "info")
            verify_ok, verify_out = run_command([str(python_path), "-c", "import mmcv; print('mmcv OK:', mmcv.__version__)"])
            if not verify_ok or "mmcv OK" not in verify_out:
                progress.report(2, f"mmcv could not be installed: {verify_out}", "error")
                return False
    
    progress.report(2, f"\u2713 mmcv ready: {verify_out.strip()}", "success")
    progress.report(2, "All packages installed successfully", "success")
    return True


def step_install_mm_packages(conda_path: Path):
    """Step 4: DEPRECATED - All installation now happens in step_install_pytorch."""
    progress.report(3, "Skipping (already installed in previous step)...", "success")
    return True


def step_install_dependencies(conda_path: Path, backend_dir: Path):
    """Step 5: Install other dependencies."""
    progress.report(4, "Installing additional dependencies...")
    
    # Get the actual environment path
    env_path = get_env_path(conda_path)
    if not env_path:
        progress.report(4, "Failed to locate environment path", "error")
        return False
    
    pip_path = pip_executable_from_env(env_path)
    
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
    
    # Copy model config files AND weights if present
    # Check multiple possible locations for bundled models
    possible_model_sources = [
        backend_dir / "models" / "cavfish_v1",  # Direct path
        backend_dir / "_up_" / "_up_" / "models" / "cavfish_v1",  # Tauri bundled path
        backend_dir / ".." / ".." / "models" / "cavfish_v1",  # Parent directory navigation
    ]
    
    models_src = None
    for candidate in possible_model_sources:
        if candidate.exists() and (candidate / "weights.pth").exists():
            models_src = candidate
            progress.report(6, f"Found bundled models at: {models_src}", "info")
            break
    
    models_dest = app_data_dir / "models" / "cavfish_v1"
    models_dest.mkdir(parents=True, exist_ok=True)
    
    if models_src and models_src.exists():
        # Copy config files
        for config_file in ["meta.json", "config.py", "config_infer.py"]:
            src = models_src / config_file
            dest = models_dest / config_file
            if src.exists() and not dest.exists():
                try:
                    shutil.copy2(src, dest)
                    progress.report(6, f"Copied {config_file}", "info")
                except Exception as e:
                    progress.report(6, f"Failed to copy {config_file}: {e}", "warning")
        
        # Copy weights if present and not already in destination
        weights_src = models_src / "weights.pth"
        weights_dest = models_dest / "weights.pth"
        if weights_src.exists() and not weights_dest.exists():
            try:
                file_size_mb = weights_src.stat().st_size / 1024 / 1024
                progress.report(6, f"Copying model weights ({file_size_mb:.1f} MB) - this may take a moment...", "info")
                shutil.copy2(weights_src, weights_dest)
                progress.report(6, f"✅ Model weights copied ({file_size_mb:.1f} MB)", "success")
            except Exception as e:
                progress.report(6, f"Failed to copy weights: {e}", "warning")
    else:
        progress.report(6, "No bundled models found - weights will need to be provided manually", "warning")
    
    # CRITICAL: Verify weights exist before marking setup complete
    weights_path = models_dest / "weights.pth"
    if not weights_path.exists():
        progress.report(6, "Model weights not found - setup incomplete", "error")
        progress.report(6, f"Expected weights at: {weights_path}", "error")
        return False
    
    # Verify weights file size (should be ~1GB)
    weights_size_mb = weights_path.stat().st_size / 1024 / 1024
    if weights_size_mb < 1:
        progress.report(6, f"Model weights file too small ({weights_size_mb:.1f} MB) - corrupted?", "error")
        return False
    
    progress.report(6, f"Model weights verified ({weights_size_mb:.1f} MB)", "success")
    
    # Save configuration
    config = {
        "setup_complete": True,
        "conda_env": ENV_NAME,
        "conda_path": str(conda_path),
        "backend_dir": str(backend_dest),
        "models_dir": str(app_data_dir / "models"),
        "weights_verified": True,
        "weights_size_mb": weights_size_mb,
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
    
    parser = argparse.ArgumentParser(description="PhenoAI Setup")
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
