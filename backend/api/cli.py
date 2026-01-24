# backend/api/cli.py
from __future__ import annotations

import argparse
import os
import uvicorn

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # fish-desktop-tool/
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0, help="0 = choose a free port")
    args = ap.parse_args()

    # uvicorn with port 0 does not always behave the way you expect across platforms.
    # For simplicity, choose a port via env var in Tauri, otherwise default 8008.
    port = args.port if args.port != 0 else int(os.environ.get("FISH_PORT", "8008"))

    uvicorn.run("backend.api.app:app", host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()

