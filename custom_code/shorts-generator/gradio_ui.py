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


async def list_previous_generations(limit: int = 50) -> list[dict[str, Any]]:
    """List previous generations.

    Args:
        limit: Maximum number to return

    Returns:
        List of generation items
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_BASE_URL}/api/list-generations?limit={limit}")
            response.raise_for_status()
            data = response.json()
            generations: list[dict[str, Any]] = data.get("generations", [])
            return generations
        except Exception:
            return []


def load_previous_generation(
    selected_index: int, generations_data: list[dict[str, Any]]
) -> tuple[str | None, str | None]:
    """Load a previous generation for display.

    Args:
        selected_index: Index of selected generation
        generations_data: List of generation data

    Returns:
        Tuple of (image_path, video_path)
    """
    if selected_index < 0 or selected_index >= len(generations_data):
        return None, None

    gen = generations_data[selected_index]
    image_path: str | None = None
    video_path: str | None = None

    # Download image if available
    if gen.get("has_image") and gen.get("image_url"):
        try:
            filename = gen["image_url"].split("/")[-1]
            download_url = f"{API_BASE_URL}/api/download/{filename}"

            with httpx.Client(timeout=30.0) as client:
                response = client.get(download_url)
                response.raise_for_status()

                from pathlib import Path

                temp_dir = Path("downloads")
                temp_dir.mkdir(exist_ok=True)
                image_path = str(temp_dir / filename)

                with open(image_path, "wb") as f:
                    f.write(response.content)
        except Exception:
            pass

    # Download video if available
    if gen.get("has_video") and gen.get("video_url"):
        try:
            filename = gen["video_url"].split("/")[-1]
            download_url = f"{API_BASE_URL}/api/download/{filename}"

            with httpx.Client(timeout=60.0) as client:
                response = client.get(download_url)
                response.raise_for_status()

                from pathlib import Path

                temp_dir = Path("downloads")
                temp_dir.mkdir(exist_ok=True)
                video_path = str(temp_dir / filename)

                with open(video_path, "wb") as f:
                    f.write(response.content)
        except Exception:
            pass

    return image_path, video_path


def generate_and_poll() -> Generator[tuple[str, str, str | None, str | None], None, None]:
    """Generate and poll for results with streaming updates.

    Yields:
        Tuples of (status, quote, image_path, video_path)
    """
    # Trigger generation
    execution_id, status_msg = asyncio.run(trigger_generation())

    if not execution_id:
        yield ("Error", status_msg, None, None)
        return

    yield (f"Started (ID: {execution_id})", "Generating...", None, None)

    # Poll for completion
    max_attempts = 300  # 5 minutes with 1s intervals (videos take longer)
    attempt = 0

    while attempt < max_attempts:
        data = asyncio.run(poll_status(execution_id))
        status = data.get("status", "unknown")

        if status == "error":
            error_msg = data.get("error", "Unknown error")
            yield (f"Error: {error_msg}", "", None, None)
            return

        if status == "success":
            quote = str(data.get("quote", ""))
            image_url = str(data.get("image_url", ""))
            video_url = str(data.get("video_url", ""))

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
                    pass  # Continue even if image download fails

            # Download video
            video_path: str | None = None
            if video_url:
                try:
                    filename = video_url.split("/")[-1]
                    download_url = f"{API_BASE_URL}/api/download/{filename}"

                    with httpx.Client(timeout=60.0) as client:
                        response = client.get(download_url)
                        response.raise_for_status()

                        # Save to temp file
                        from pathlib import Path

                        temp_dir = Path("downloads")
                        temp_dir.mkdir(exist_ok=True)
                        video_path = str(temp_dir / filename)

                        with open(video_path, "wb") as f:
                            f.write(response.content)

                except Exception:
                    pass  # Continue even if video download fails

            # Determine final status message
            if image_path and video_path:
                status_msg = "Success! Image and video generated."
            elif image_path:
                status_msg = "Success! Image generated (video pending or failed)."
            elif video_path:
                status_msg = "Success! Video generated (image failed)."
            else:
                status_msg = "Success (but downloads failed)"

            yield (status_msg, quote, image_path, video_path)
            return

        # Still running - provide more detailed status for long-running operations
        status_str = str(status) if status else "unknown"
        if attempt > 60:
            status_str = f"{status_str} (generating video...)"
        yield (f"{status_str.capitalize()}...", "Processing...", None, None)

        time.sleep(1)
        attempt += 1

    yield ("Timeout", "Generation took too long", None, None)


def create_ui() -> Any:
    """Create Gradio interface."""
    with gr.Blocks(title="Inspirational Shorts Generator") as demo:
        gr.Markdown(
            """
            # Inspirational Shorts Generator
            Generate trauma-informed inspirational quotes with AI-generated imagery and videos.

            This workflow creates:
            1. **Quote**: Compassionate, trauma-informed inspirational text
            2. **Image**: Photorealistic 9:16 portrait (via ComfyUI + HiDream)
            3. **Video**: 10-second animated video with synchronized audio (via Ovi 11B)
            """
        )

        with gr.Tabs():
            with gr.Tab("Generate New"):
                with gr.Row():
                    with gr.Column():
                        status_box = gr.Textbox(
                            label="Status",
                            value="Ready",
                            interactive=False,
                        )

                        generate_btn = gr.Button("Generate Quote, Image & Video", variant="primary")

                        quote_output = gr.Textbox(
                            label="Generated Quote",
                            lines=3,
                            interactive=False,
                        )

                    with gr.Column():
                        image_output = gr.Image(
                            label="Generated Image (9:16)",
                            type="filepath",
                            interactive=False,
                            height=600,
                            show_download_button=True,
                        )

                        video_output = gr.Video(
                            label="Generated Video (10s with audio)",
                            interactive=False,
                            height=600,
                            show_download_button=True,
                        )

                # Wire up generation
                generate_btn.click(
                    fn=generate_and_poll,
                    inputs=[],
                    outputs=[status_box, quote_output, image_output, video_output],
                )

                gr.Markdown(
                    """
                    ---
                    **Note:** Generation typically takes 3-5 minutes.
                    - **Quote generation**: ~5 seconds (Claude Sonnet 4.5)
                    - **Image generation**: ~30-60 seconds (ComfyUI + HiDream model)
                    - **Video generation**: ~2-4 minutes (Ovi 11B 10-second video+audio model)

                    The video includes synchronized speech and ambient audio based on the quote.
                    """
                )

            with gr.Tab("Browse Previous"):
                # Hidden state to store generations data
                generations_state = gr.State([])

                with gr.Row():
                    refresh_btn = gr.Button("Refresh List", variant="secondary")
                    generation_count = gr.Textbox(
                        label="Total Generations",
                        value="0",
                        interactive=False,
                        scale=1,
                    )

                generation_selector = gr.Dropdown(
                    label="Select Generation",
                    choices=[],
                    value=None,
                    interactive=True,
                    scale=3,
                    allow_custom_value=False,
                )

                with gr.Row():
                    with gr.Column():
                        prev_image = gr.Image(
                            label="Image",
                            type="filepath",
                            interactive=False,
                            height=600,
                            show_download_button=True,
                        )
                    with gr.Column():
                        prev_video = gr.Video(
                            label="Video",
                            interactive=False,
                            height=600,
                            show_download_button=True,
                        )

                def refresh_generations() -> tuple[gr.Dropdown, str, list[dict[str, Any]]]:
                    """Refresh the list of previous generations."""
                    gens = asyncio.run(list_previous_generations())
                    choices = []
                    for g in gens:
                        parts = []
                        if g.get("has_image"):
                            parts.append("Image")
                        if g.get("has_video"):
                            parts.append("Video")
                        label = f"{g['timestamp']} - {' + '.join(parts)}"
                        choices.append(label)
                    # Return a Dropdown update with choices but no value set
                    return gr.Dropdown(choices=choices, value=None), str(len(gens)), gens

                def on_select(
                    selected: str | None, gens: list[dict[str, Any]]
                ) -> tuple[str | None, str | None]:
                    """Handle generation selection."""
                    if not selected or not gens:
                        return None, None
                    # Find index from dropdown choice
                    try:
                        for i, g in enumerate(gens):
                            timestamp = g["timestamp"]
                            if selected.startswith(timestamp):
                                return load_previous_generation(i, gens)
                    except Exception:
                        pass
                    return None, None

                # Wire up browse tab
                refresh_btn.click(
                    fn=refresh_generations,
                    inputs=[],
                    outputs=[generation_selector, generation_count, generations_state],
                )

                generation_selector.change(
                    fn=on_select,
                    inputs=[generation_selector, generations_state],
                    outputs=[prev_image, prev_video],
                )

                # Auto-load on tab open
                demo.load(
                    fn=refresh_generations,
                    inputs=[],
                    outputs=[generation_selector, generation_count, generations_state],
                )

    return demo


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860)
