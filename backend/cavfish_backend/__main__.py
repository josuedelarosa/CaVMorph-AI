"""
Backend server entry point.
Usage: python -m cavfish_backend serve --port 8008
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Fish Morphometrics Backend Server")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    serve_parser = subparsers.add_parser("serve", help="Start the backend server")
    serve_parser.add_argument("--port", type=int, default=8008, help="Port to listen on")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--device", type=str, default="cpu", help="Device: cpu or cuda")
    serve_parser.add_argument("--log-level", type=str, default="info", help="Log level")
    
    args = parser.parse_args()
    
    if args.command == "serve":
        import os
        os.environ["FISH_DEVICE"] = args.device
        
        # Import after setting env vars
        from .server import start_server
        start_server(host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
