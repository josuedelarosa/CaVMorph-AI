"""
FastAPI server implementation.
"""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))


def start_server(host: str = "127.0.0.1", port: int = 8008, log_level: str = "info"):
    """Start the uvicorn server."""
    import uvicorn
    from api.app import app
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
    )
