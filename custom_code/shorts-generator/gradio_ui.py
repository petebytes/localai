"""Gradio web interface for shorts generator."""

import asyncio
import os
import time
from collections.abc import Generator
from typing import Any

import gradio as gr
import httpx

# API configuration removed - prompts are now hardcoded in backend

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


async def trigger_generation() -> tuple[str, str]:
    """Trigger workflow generation via API.

    Returns:
        Tuple of (execution_id, status_message)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/generate",
                json={},
            )
            response.raise_for_status()
            data = response.json()
            return data["execution_id"], "Generation started"
        except Exception as e:
            return "", f"Error: {str(e)}"


async def poll_status(execution_id: str) -> dict[str, str]:
    """Poll execution status via API.

    Args:
        execution_id: Execution ID to poll

    Returns:
        Response data dict
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_BASE_URL}/api/status/{execution_id}")
            response.raise_for_status()
            data: dict[str, str] = response.json()
            return data
        except Exception as e:
            return {"status": "error", "error": str(e)}


def generate_and_poll() -> Generator[tuple[str, str, str | None], None, None]:
    """Generate and poll for results with streaming updates.

    Yields:
        Tuples of (status, quote, image_path)
    """
    # Trigger generation
    execution_id, status_msg = asyncio.run(trigger_generation())

    if not execution_id:
        yield ("Error", status_msg, None)
        return

    yield (f"Started (ID: {execution_id})", "Generating...", None)

    # Poll for completion
    max_attempts = 120  # 2 minutes with 1s intervals
    attempt = 0

    while attempt < max_attempts:
        data = asyncio.run(poll_status(execution_id))
        status = data.get("status", "unknown")

        if status == "error":
            error_msg = data.get("error", "Unknown error")
            yield (f"Error: {error_msg}", "", None)
            return

        if status == "success":
            quote = str(data.get("quote", ""))
            image_url = str(data.get("image_url", ""))

            # Download image
            image_path: str | None = None
            if image_url:
                try:
                    filename = image_url.split("/")[-1]
                    download_url = f"{API_BASE_URL}/api/download/{filename}"

                    with httpx.Client(timeout=30.0) as client:
                        response = client.get(download_url)
                        response.raise_for_status()

                        # Save to temp file
                        from pathlib import Path

                        temp_dir = Path("downloads")
                        temp_dir.mkdir(exist_ok=True)
                        image_path = str(temp_dir / filename)

                        with open(image_path, "wb") as f:
                            f.write(response.content)

                except Exception:
                    yield ("Success (image download failed)", quote, None)
                    return

            yield ("Success!", quote, image_path)
            return

        # Still running
        status_str = str(status) if status else "unknown"
        yield (f"{status_str.capitalize()}...", "Processing...", None)

        time.sleep(1)
        attempt += 1

    yield ("Timeout", "Generation took too long", None)


def create_ui() -> Any:
    """Create Gradio interface."""
    with gr.Blocks(title="Inspirational Shorts Generator") as demo:
        gr.Markdown(
            """
            # Inspirational Quote Image Generator
            Generate trauma-informed inspirational quotes with AI-generated imagery.
            """
        )

        with gr.Row():
            with gr.Column():
                status_box = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                )

                generate_btn = gr.Button("Generate Quote & Image", variant="primary")

                quote_output = gr.Textbox(
                    label="Generated Quote",
                    lines=3,
                    interactive=False,
                )

            with gr.Column():
                image_output = gr.Image(
                    label="Generated Image",
                    type="filepath",
                    interactive=False,
                )

        # Wire up generation
        generate_btn.click(
            fn=generate_and_poll,
            inputs=[],
            outputs=[status_box, quote_output, image_output],
        )

        gr.Markdown(
            """
            ---
            **Note:** Generation typically takes 30-60 seconds.
            The workflow uses Claude Sonnet 4.5 for text generation
            and ComfyUI + HiDream for image generation.
            """
        )

    return demo


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860)
