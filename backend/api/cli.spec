# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for cavfish-inference backend.

Usage:
  pyinstaller backend/api/cli.spec

This creates a self-contained executable that can be bundled with Tauri.
"""

import os
import sys
from pathlib import Path

# Get absolute paths
ROOT = Path.cwd()
BACKEND = ROOT / "backend"

block_cipher = None

a = Analysis(
    [str(BACKEND / "api" / "cli.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=[
        (str(ROOT / "models"), "models"),
        (str(BACKEND / "phenolosses"), "phenolosses"),
        (str(BACKEND / "third_party"), "third_party"),
        (str(BACKEND / "custom_transforms.py"), "."),
    ],
    hiddenimports=[
        "mmpose",
        "mmengine",
        "mmpretrain",
        "torch",
        "torchvision",
        "numpy",
        "cv2",
        "fastapi",
        "uvicorn",
        "pydantic",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websocket.auto",
        "uvicorn.protocols.websocket.wsproto_impl",
        "uvicorn.server",
        "uvicorn.config",
        "uvicorn.supervisors",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        "matplotlib",
        "tkinter",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="fish_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
