"""
Zachry Open Worlds Studio - Entry Point

Usage:
    python -m gui.main
"""

import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

# Ensure project root is on sys.path for upstream imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

PORT = 8420
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"


def open_browser():
    """Wait for server to start, then open browser."""
    time.sleep(1.5)
    webbrowser.open(URL)


def main():
    print(f"\n  Zachry Open Worlds Studio")
    print(f"  Video Depth Anything GUI")
    print(f"  {URL}\n")

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    from gui.api.server import create_app

    app = create_app()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
