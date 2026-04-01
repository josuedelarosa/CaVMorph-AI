#!/usr/bin/env python3
"""
prepare_runtime.py — Build a portable, self-contained Python runtime for Fishometrics.

Downloads a standalone CPython interpreter (from python-build-standalone),
pre-installs every package the ONNX inference backend needs, and places the
tree under desktop/runtime/python/ so that `npm run tauri build` bundles it
into the installer — giving end-users a true zero-install experience.

Supported targets
-----------------
  windows / x64
  macos   / x64, arm64
  linux   / x64, arm64

Usage
-----
    python scripts/prepare_runtime.py                        # auto-detect
    python scripts/prepare_runtime.py --clean                # wipe & rebuild
    python scripts/prepare_runtime.py --platform macos --arch arm64
    python scripts/prepare_runtime.py --skip-packages        # debug: skip pip
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# Tunables  (bump these when upgrading the bundled Python version)
# ────────────────────────────────────────────────────────────────────────────
PYTHON_VERSION = "3.12.8"
PBS_TAG = "20241206"  # python-build-standalone release tag
PBS_BASE_URL = (
    "https://github.com/indygreg/python-build-standalone/releases/"
    f"download/{PBS_TAG}"
)

# (platform, arch) → archive filename
ARCHIVE_MAP: dict[tuple[str, str], str] = {
    ("windows", "x64"): (
        f"cpython-{PYTHON_VERSION}+{PBS_TAG}"
        "-x86_64-pc-windows-msvc-install_only.tar.gz"
    ),
    ("macos", "x64"): (
        f"cpython-{PYTHON_VERSION}+{PBS_TAG}"
        "-x86_64-apple-darwin-install_only.tar.gz"
    ),
    ("macos", "arm64"): (
        f"cpython-{PYTHON_VERSION}+{PBS_TAG}"
        "-aarch64-apple-darwin-install_only.tar.gz"
    ),
    ("linux", "x64"): (
        f"cpython-{PYTHON_VERSION}+{PBS_TAG}"
        "-x86_64-unknown-linux-gnu-install_only.tar.gz"
    ),
    ("linux", "arm64"): (
        f"cpython-{PYTHON_VERSION}+{PBS_TAG}"
        "-aarch64-unknown-linux-gnu-install_only.tar.gz"
    ),
}

PACKAGES = [
    "onnxruntime>=1.17.0",
    "numpy>=1.24.0,<2.0",
    "opencv-python-headless>=4.8.0",
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "pillow>=9.0.0",
]

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / "desktop" / "runtime" / "python"


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[prepare_runtime] {msg}", flush=True)


def detect_platform() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    os_map = {"windows": "windows", "darwin": "macos", "linux": "linux"}
    os_name = os_map.get(system)
    if os_name is None:
        sys.exit(f"Unsupported OS: {system}")

    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        sys.exit(f"Unsupported architecture: {machine}")

    return os_name, arch


def get_download_url(os_name: str, arch: str) -> str:
    key = (os_name, arch)
    if key not in ARCHIVE_MAP:
        sys.exit(f"No archive configured for {os_name}/{arch}")
    return f"{PBS_BASE_URL}/{ARCHIVE_MAP[key]}"


def download_file(url: str, dest: Path) -> None:
    log(f"Downloading {url}")

    def _progress(count: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            pct = min(100, int(count * block_size * 100 / total_size))
            mb = count * block_size / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r  {mb:.1f} / {total_mb:.1f} MB ({pct}%)", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), reporthook=_progress)
    print()
    log(f"Download complete ({dest.stat().st_size / (1024 * 1024):.1f} MB)")


def extract_archive(archive: Path, dest: Path) -> None:
    log(f"Extracting to {dest}")
    dest.mkdir(parents=True, exist_ok=True)

    with tarfile.open(str(archive), "r:gz") as tar:
        # Security: validate all members stay inside dest
        for member in tar.getmembers():
            member_path = (dest / member.name).resolve()
            if not str(member_path).startswith(str(dest.resolve())):
                sys.exit(f"Tar member escapes target: {member.name}")
        tar.extractall(str(dest), filter="data" if hasattr(tarfile, "data_filter") else None)

    # PBS archives extract into a python/ sub-directory — flatten it.
    extracted = dest / "python"
    if extracted.is_dir():
        for item in list(extracted.iterdir()):
            target = dest / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))
        extracted.rmdir()

    log("Extraction complete")


def python_exe(runtime_dir: Path, os_name: str) -> Path:
    if os_name == "windows":
        exe = runtime_dir / "python.exe"
    else:
        exe = runtime_dir / "bin" / "python3"
    if not exe.exists():
        # Fallback: try python (no version suffix)
        alt = runtime_dir / ("python.exe" if os_name == "windows" else "bin/python")
        if alt.exists():
            return alt
        sys.exit(f"Python executable not found at {exe}")
    return exe


def install_packages(py: Path, packages: list[str]) -> None:
    log("Upgrading pip…")
    subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "--no-warn-script-location", "pip"],
        capture_output=True,
    )

    log(f"Installing {len(packages)} packages (this will take a few minutes)…")
    # --force-reinstall ensures every package lands in the portable runtime's
    # site-packages even if the same version exists in the build-machine's
    # system Python (which pip may otherwise silently reuse).
    cmd = [
        str(py), "-m", "pip", "install",
        "--no-warn-script-location",
        "--force-reinstall",
    ] + packages
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        sys.exit("Package installation failed")
    log("All packages installed")


def verify_runtime(py: Path) -> None:
    log("Verifying runtime imports…")
    check = (
        "import onnxruntime, numpy, cv2, fastapi, uvicorn, pydantic; "
        "print('OK')"
    )
    result = subprocess.run([str(py), "-c", check], capture_output=True, text=True)
    if result.returncode != 0 or "OK" not in result.stdout:
        print(result.stderr, file=sys.stderr)
        sys.exit("Runtime verification failed — imports broken")
    log("All packages verified ✓")


def write_manifest(runtime_dir: Path, os_name: str, arch: str) -> None:
    manifest = {
        "python_version": PYTHON_VERSION,
        "pbs_tag": PBS_TAG,
        "platform": os_name,
        "arch": arch,
        "packages": PACKAGES,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (runtime_dir / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2))
    log("Manifest written")


def dir_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (1024 * 1024)


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare portable Python for Fishometrics")
    parser.add_argument("--platform", choices=["windows", "macos", "linux"])
    parser.add_argument("--arch", choices=["x64", "arm64"])
    parser.add_argument("--clean", action="store_true", help="Wipe existing runtime first")
    parser.add_argument("--skip-packages", action="store_true", help="Skip pip install (debug)")
    args = parser.parse_args()

    detected_os, detected_arch = detect_platform()
    os_name = args.platform or detected_os
    arch = args.arch or detected_arch

    log(f"Target: {os_name}/{arch}")
    log(f"Python: {PYTHON_VERSION}  (PBS tag {PBS_TAG})")
    log(f"Runtime dir: {RUNTIME_DIR}")

    # ── Clean / skip ────────────────────────────────────────────────────────
    manifest_path = RUNTIME_DIR / "runtime_manifest.json"

    if args.clean and RUNTIME_DIR.exists():
        log("Cleaning existing runtime…")
        readme_text = None
        readme_path = RUNTIME_DIR / "README.md"
        if readme_path.exists():
            readme_text = readme_path.read_text()
        shutil.rmtree(RUNTIME_DIR)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        if readme_text:
            readme_path.write_text(readme_text)
    elif manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
            if (
                existing.get("platform") == os_name
                and existing.get("arch") == arch
                and existing.get("python_version") == PYTHON_VERSION
            ):
                log("Runtime already prepared for this target — use --clean to rebuild")
                return
            log(
                f"Platform/version changed "
                f"({existing.get('platform')}/{existing.get('arch')} "
                f"→ {os_name}/{arch}), rebuilding…"
            )
            shutil.rmtree(RUNTIME_DIR)
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        except (json.JSONDecodeError, KeyError):
            pass

    # ── Download ────────────────────────────────────────────────────────────
    url = get_download_url(os_name, arch)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"python-{PYTHON_VERSION}.tar.gz"
        download_file(url, archive)
        extract_archive(archive, RUNTIME_DIR)

    # ── Python sanity check ─────────────────────────────────────────────────
    py = python_exe(RUNTIME_DIR, os_name)
    log(f"Python executable: {py}")
    result = subprocess.run([str(py), "--version"], capture_output=True, text=True)
    log(f"Version: {result.stdout.strip()}")

    # ── Packages ────────────────────────────────────────────────────────────
    if not args.skip_packages:
        install_packages(py, PACKAGES)
        verify_runtime(py)

    # ── Finalize ────────────────────────────────────────────────────────────
    write_manifest(RUNTIME_DIR, os_name, arch)
    size = dir_size_mb(RUNTIME_DIR)
    log(f"Total runtime size: {size:.0f} MB")
    log("Done! Now run:  cd desktop && npm run tauri build")


if __name__ == "__main__":
    main()
