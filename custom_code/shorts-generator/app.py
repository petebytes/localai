"""Unified launcher for FastAPI backend and Gradio frontend."""

import os
import threading

import uvicorn

from api import app as fastapi_app
from gradio_ui import create_ui


def run_fastapi() -> None:
    """Run FastAPI server in separate thread."""
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


def main() -> None:
    """Launch both FastAPI and Gradio."""
    # Set API base URL for Gradio to find FastAPI
    os.environ["API_BASE_URL"] = "http://localhost:8000"

    # Start FastAPI in background thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # Give FastAPI time to start
    import time

    time.sleep(2)

    # Launch Gradio in main thread (blocking)
    ui = create_ui()
    ui.queue()  # Enable queuing for progress indicators
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )


if __name__ == "__main__":
    main()
