# backend/api/cli.py
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Setup paths for both dev and frozen (PyInstaller) modes
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        BUNDLE_DIR = Path(sys._MEIPASS)
    else:
        BUNDLE_DIR = Path(os.path.dirname(sys.executable))
    
    if str(BUNDLE_DIR) not in sys.path:
        sys.path.insert(0, str(BUNDLE_DIR))
else:
    # Running in development or from copied backend
    _THIS_FILE = Path(__file__).resolve()
    _API_DIR = _THIS_FILE.parent
    _BACKEND_DIR = _API_DIR.parent
    
    # Add backend directory to path
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))
    
    # Also add parent for dev mode
    _ROOT = _BACKEND_DIR.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

import uvicorn
import multiprocessing


def main():
    multiprocessing.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0, help="0 = choose a free port")
    args = ap.parse_args()

    # uvicorn with port 0 does not always behave the way you expect across platforms.
    # For simplicity, choose a port via env var in Tauri, otherwise default 8008.
    port = args.port if args.port != 0 else int(os.environ.get("FISH_PORT", "8008"))

    # Import app after path setup
    try:
        from api.app import app
        uvicorn.run(app, host=args.host, port=port, log_level="info")
    except ImportError:
        # Fallback for dev mode
        uvicorn.run("backend.api.app:app", host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()

