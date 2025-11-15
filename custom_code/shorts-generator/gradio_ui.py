"""Gradio web interface for shorts generator."""

import asyncio
import os
import sys
import time
from collections.abc import Generator
from typing import Any

import gradio as gr
import httpx

# API configuration removed - prompts are now hardcoded in backend

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def download_file_from_api(filename: str, timeout: float = 30.0) -> str | None:
    """Download a file from the API and save to temp directory.

    Args:
        filename: Name of file to download
        timeout: Request timeout in seconds

    Returns:
        Path to downloaded file, or None if download failed
    """
    try:
        download_url = f"{API_BASE_URL}/api/download/{filename}"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(download_url)
            response.raise_for_status()

            from pathlib import Path

            temp_dir = Path("downloads")
            temp_dir.mkdir(exist_ok=True)
            file_path = str(temp_dir / filename)

            with open(file_path, "wb") as f:
                f.write(response.content)

            return file_path
    except Exception as e:
        print(f"Failed to download {filename}: {e}", file=sys.stderr)
        return None


async def trigger_generation(custom_quote: str | None = None) -> tuple[str, str]:
    """Trigger workflow generation via API.

    Args:
        custom_quote: Optional custom quote to use instead of AI-generated

    Returns:
        Tuple of (execution_id, status_message)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Prepare request payload
            payload = {}
            if custom_quote and custom_quote.strip():
                payload["custom_quote"] = custom_quote.strip()

            response = await client.post(
                f"{API_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["execution_id"], "Generation started"
        except Exception as e:
            return "", f"Error: {str(e)}"


async def approve_quote(
    execution_id: str, action: str, resume_url: str, edited_quote: str | None = None
) -> tuple[bool, str]:
    """Send quote approval decision to API.

    Args:
        execution_id: Execution ID to approve
        action: Approval action (approve/edit/reject)
        resume_url: Resume webhook URL from n8n
        edited_quote: Optional edited quote text

    Returns:
        Tuple of (success, message)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            payload = {"execution_id": execution_id, "action": action, "resume_url": resume_url}
            if edited_quote and action == "edit":
                payload["edited_quote"] = edited_quote.strip()

            print(f"📤 Sending approval to API: {payload}", file=sys.stderr)
            response = await client.post(
                f"{API_BASE_URL}/api/approve-quote",
                json=payload,
            )
            print(f"📥 API response: status={response.status_code}", file=sys.stderr)
            response.raise_for_status()
            data = response.json()
            return data["success"], data["message"]
        except Exception as e:
            print(f"❌ Approval error: {e}", file=sys.stderr)
            return False, f"Error: {str(e)}"


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

    # Download image if available
    image_path: str | None = None
    if gen.get("has_image") and gen.get("image_url"):
        filename = gen["image_url"].split("/")[-1]
        image_path = download_file_from_api(filename, timeout=30.0)

    # Download video if available
    video_path: str | None = None
    if gen.get("has_video") and gen.get("video_url"):
        filename = gen["video_url"].split("/")[-1]
        video_path = download_file_from_api(filename, timeout=60.0)

    return image_path, video_path


def generate_and_poll(
    custom_quote: str | None = None,
) -> Generator[tuple[str, str, str | None, str | None, str, str, bool], None, None]:
    """Generate and poll for results with streaming updates.

    Args:
        custom_quote: Optional custom quote to use

    Yields:
        Tuples of (status, quote, image_path, video_path, execution_id,
            resume_url, waiting_for_approval)
    """
    # Trigger generation
    execution_id, status_msg = asyncio.run(trigger_generation(custom_quote))

    if not execution_id:
        yield ("Error", status_msg, None, None, "", "", False)
        return

    yield (f"Started (ID: {execution_id})", "Generating...", None, None, execution_id, "", False)

    # Poll for completion
    max_attempts = 300  # 5 minutes with 1s intervals (videos take longer)
    attempt = 0

    while attempt < max_attempts:
        data = asyncio.run(poll_status(execution_id))
        status = data.get("status", "unknown")

        if status == "error":
            error_msg = data.get("error", "Unknown error")
            yield (f"Error: {error_msg}", "", None, None, execution_id, "", False)
            return

        if status == "waiting_for_approval":
            quote = str(data.get("quote", ""))
            resume_url = str(data.get("resume_url", ""))
            print(f"🔔 WAITING FOR APPROVAL! Quote: {quote[:50]}", file=sys.stderr)
            yield (
                "Waiting for approval",
                quote,
                None,
                None,
                execution_id,
                resume_url,
                True,  # Signal that we need approval
            )
            print("✅ Yielded approval state: waiting=True", file=sys.stderr)
            return  # Stop polling, wait for user action

        if status == "success":
            quote = str(data.get("quote", ""))
            image_url = str(data.get("image_url", ""))
            video_url = str(data.get("video_url", ""))

            # Download image
            image_path: str | None = None
            if image_url:
                filename = image_url.split("/")[-1]
                image_path = download_file_from_api(filename, timeout=30.0)

            # Download video
            video_path: str | None = None
            if video_url:
                filename = video_url.split("/")[-1]
                video_path = download_file_from_api(filename, timeout=60.0)

            # Determine final status message
            if image_path and video_path:
                status_msg = "Success! Image and video generated."
            elif image_path:
                status_msg = "Success! Image generated (video pending or failed)."
            elif video_path:
                status_msg = "Success! Video generated (image failed)."
            else:
                status_msg = "Success (but downloads failed)"

            yield (status_msg, quote, image_path, video_path, execution_id, "", False)
            return

        # Still running - provide more detailed status for long-running operations
        status_str = str(status) if status else "unknown"
        if attempt > 60:
            status_str = f"{status_str} (generating video...)"
        yield (
            f"{status_str.capitalize()}...",
            "Processing...",
            None,
            None,
            execution_id,
            "",
            False,
        )

        time.sleep(1)
        attempt += 1

    yield ("Timeout", "Generation took too long", None, None, execution_id, "", False)


def resume_polling(
    execution_id: str,
) -> Generator[tuple[str, str, str | None, str | None, str, str, bool], None, None]:
    """Resume polling for an existing execution.

    Args:
        execution_id: Execution ID to resume polling for

    Yields:
        Tuples of (status, quote, image_path, video_path, execution_id,
            resume_url, waiting_for_approval)
    """
    if not execution_id or not execution_id.strip():
        yield ("Error: Please enter a valid execution ID", "", None, None, "", "", False)
        return

    yield (f"Resuming polling for {execution_id}...", "", None, None, execution_id, "", False)

    # Poll for completion (same logic as generate_and_poll but starting from resume)
    max_attempts = 300
    attempt = 0

    while attempt < max_attempts:
        time.sleep(1)
        data = asyncio.run(poll_status(execution_id))
        status = data.get("status", "unknown")

        if status == "error":
            error_msg = data.get("error", "Unknown error")
            yield (f"Error: {error_msg}", "", None, None, execution_id, "", False)
            return

        if status == "waiting_for_approval":
            quote = str(data.get("quote", ""))
            resume_url = str(data.get("resume_url", ""))
            yield (
                "Waiting for approval",
                quote,
                None,
                None,
                execution_id,
                resume_url,
                True,
            )
            return

        if status == "success":
            quote = str(data.get("quote", ""))
            image_url = str(data.get("image_url", ""))
            video_url = str(data.get("video_url", ""))

            image_path: str | None = None
            if image_url:
                filename = image_url.split("/")[-1]
                image_path = download_file_from_api(filename, timeout=30.0)

            video_path: str | None = None
            if video_url:
                filename = video_url.split("/")[-1]
                video_path = download_file_from_api(filename, timeout=60.0)

            if image_path and video_path:
                status_msg = "Success! Image and video generated."
            elif image_path:
                status_msg = "Success! Image generated (video pending or failed)."
            elif video_path:
                status_msg = "Success! Video generated (image failed)."
            else:
                status_msg = "Success (but downloads failed)"

            yield (status_msg, quote, image_path, video_path, execution_id, "", False)
            return

        # Still running
        status_str = str(status) if status else "unknown"
        if attempt > 60:
            status_str = f"{status_str} (may take 3-5 min total...)"
        yield (
            f"{status_str.capitalize()}...",
            "",
            None,
            None,
            execution_id,
            "",
            False,
        )

        attempt += 1

    yield (
        f"Timeout: Execution may still be running. Use 'Resume Generation' with ID: {execution_id}",
        "",
        None,
        None,
        execution_id,
        "",
        False,
    )


def continue_after_approval(
    execution_id: str, resume_url: str, action: str, edited_quote: str | None = None
) -> Generator[tuple[str, str, str | None, str | None, str, str, bool], None, None]:
    """Continue workflow after quote approval.

    Args:
        execution_id: Execution ID to continue
        resume_url: Resume webhook URL from n8n
        action: Approval action (approve/edit/reject)
        edited_quote: Optional edited quote

    Yields:
        Tuples of (status, quote, image_path, video_path, execution_id,
            resume_url, waiting_for_approval)
    """
    print(
        f"🚀 continue_after_approval called: exec_id={execution_id}, action={action}",
        file=sys.stderr,
    )

    # Send approval
    success, message = asyncio.run(approve_quote(execution_id, action, resume_url, edited_quote))
    print(f"📡 Approval API response: success={success}, message={message}", file=sys.stderr)

    if not success:
        yield (
            f"Approval failed: {message}. Use 'Resume Generation' to retry if needed.",
            "",
            None,
            None,
            execution_id,
            "",
            False,
        )
        return

    if action == "reject":
        yield ("Workflow cancelled", "Quote rejected by user", None, None, execution_id, "", False)
        return

    yield (f"{message}, continuing...", edited_quote or "", None, None, execution_id, "", False)

    # Continue polling for completion
    max_attempts = 300
    attempt = 0

    while attempt < max_attempts:
        time.sleep(1)
        data = asyncio.run(poll_status(execution_id))
        status = data.get("status", "unknown")

        if status == "error":
            error_msg = data.get("error", "Unknown error")
            yield (f"Error: {error_msg}", "", None, None, execution_id, "", False)
            return

        if status == "success":
            quote = str(data.get("quote", ""))
            image_url = str(data.get("image_url", ""))
            video_url = str(data.get("video_url", ""))

            # Download image
            image_path: str | None = None
            if image_url:
                filename = image_url.split("/")[-1]
                image_path = download_file_from_api(filename, timeout=30.0)

            # Download video
            video_path: str | None = None
            if video_url:
                filename = video_url.split("/")[-1]
                video_path = download_file_from_api(filename, timeout=60.0)

            # Determine final status message
            if image_path and video_path:
                status_msg = "Success! Image and video generated."
            elif image_path:
                status_msg = "Success! Image generated (video pending or failed)."
            elif video_path:
                status_msg = "Success! Video generated (image failed)."
            else:
                status_msg = "Success (but downloads failed)"

            yield (status_msg, quote, image_path, video_path, execution_id, "", False)
            return

        # Still running
        status_str = str(status) if status else "unknown"
        if attempt > 60:
            status_str = f"{status_str} (generating video...)"
        yield (
            f"{status_str.capitalize()}...",
            "Processing...",
            None,
            None,
            execution_id,
            "",
            False,
        )

        attempt += 1

    yield ("Timeout", "Generation took too long", None, None, execution_id, "", False)


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
                # Hidden state for execution ID, resume URL, and approval status
                execution_id_state = gr.State("")
                resume_url_state = gr.State("")
                waiting_for_approval_state = gr.State(False)

                with gr.Row():
                    with gr.Column():
                        custom_quote_input = gr.Textbox(
                            label="Custom Quote (Optional)",
                            placeholder=(
                                "Leave empty to generate an AI quote, "
                                "or enter your own quote here..."
                            ),
                            lines=2,
                            interactive=True,
                        )

                        status_box = gr.Textbox(
                            label="Status",
                            value="Ready",
                            interactive=False,
                        )

                        generate_btn = gr.Button("Generate Quote, Image & Video", variant="primary")

                        # Error recovery section
                        with gr.Accordion(
                            "Resume Generation", open=False, visible=False
                        ) as resume_accordion:
                            gr.Markdown(
                                """
                                If generation was interrupted, you can resume polling for
                                an existing execution. The Execution ID is shown in the
                                status above.
                                """
                            )
                            resume_exec_id = gr.Textbox(
                                label="Execution ID",
                                placeholder="Enter execution ID to resume...",
                                interactive=True,
                            )
                            resume_btn = gr.Button("Resume Polling", variant="secondary")

                        quote_output = gr.Textbox(
                            label="Generated Quote",
                            lines=3,
                            interactive=False,
                        )

                        # Approval section (initially hidden)
                        with gr.Column(visible=False) as approval_group:
                            gr.Markdown(
                                """
                                ### Quote Approval Required
                                Please review the generated quote above and choose an action:
                                """
                            )

                            edited_quote_input = gr.Textbox(
                                label="Edit Quote (Optional)",
                                placeholder=(
                                    "Edit the quote if needed, or leave as-is to approve..."
                                ),
                                lines=3,
                                interactive=True,
                            )

                            with gr.Row():
                                approve_btn = gr.Button("✓ Approve", variant="primary", scale=1)
                                edit_approve_btn = gr.Button(
                                    "✎ Edit & Approve", variant="secondary", scale=1
                                )
                                reject_btn = gr.Button("✗ Reject", variant="stop", scale=1)

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

                # Helper function to show/hide approval group and resume accordion based on status
                def update_approval_visibility(
                    status: str,
                    quote: str,
                    image: str | None,
                    video: str | None,
                    exec_id: str,
                    resume_url: str,
                    waiting: bool,
                ) -> tuple[
                    str,
                    str,
                    str | None,
                    str | None,
                    str,
                    str,
                    bool,
                    gr.Column,
                    gr.Textbox,
                    gr.Accordion,
                    gr.Textbox,
                    gr.Button,
                    gr.Button,
                    gr.Button,
                    gr.Button,
                    gr.Button,
                ]:
                    """Update UI based on approval status and show resume accordion on errors."""
                    print(f"🎯 update_approval_visibility: waiting={waiting}", file=sys.stderr)
                    # Update approval group visibility
                    approval_visible = waiting
                    # Pre-fill edited quote input with generated quote
                    edited_quote_value = quote if waiting else ""

                    # Show resume accordion on timeout or error
                    show_resume = "timeout" in status.lower() or "error" in status.lower()
                    resume_id_value = exec_id if show_resume else ""

                    # Determine button states based on status
                    is_processing = status.lower() not in [
                        "ready",
                        "success",
                        "error",
                        "timeout",
                        "workflow cancelled",
                        "waiting for approval",
                    ]
                    is_waiting_approval = waiting
                    (
                        "success" in status.lower()
                        or "error" in status.lower()
                        or "timeout" in status.lower()
                        or "cancelled" in status.lower()
                    )

                    # Generate button: disabled when processing or waiting for approval
                    generate_enabled = not is_processing and not is_waiting_approval

                    # Approval buttons: enabled only when waiting for approval
                    approval_enabled = is_waiting_approval

                    # Resume button: enabled when showing resume accordion
                    resume_enabled = show_resume

                    return (
                        status,
                        quote,
                        image,
                        video,
                        exec_id,
                        resume_url,
                        waiting,
                        gr.Column(visible=approval_visible),
                        gr.Textbox(value=edited_quote_value),
                        gr.Accordion(visible=show_resume),
                        gr.Textbox(value=resume_id_value),
                        gr.Button(interactive=generate_enabled),  # generate_btn
                        gr.Button(interactive=approval_enabled),  # approve_btn
                        gr.Button(interactive=approval_enabled),  # edit_approve_btn
                        gr.Button(interactive=approval_enabled),  # reject_btn
                        gr.Button(interactive=resume_enabled),  # resume_btn
                    )

                # Wire up generation
                generate_btn.click(
                    fn=generate_and_poll,
                    inputs=[custom_quote_input],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                ).then(
                    fn=update_approval_visibility,
                    inputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                        approval_group,
                        edited_quote_input,
                        resume_accordion,
                        resume_exec_id,
                        generate_btn,
                        approve_btn,
                        edit_approve_btn,
                        reject_btn,
                        resume_btn,
                    ],
                )

                # Wire up resume button
                resume_btn.click(
                    fn=resume_polling,
                    inputs=[resume_exec_id],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                ).then(
                    fn=update_approval_visibility,
                    inputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                        approval_group,
                        edited_quote_input,
                        resume_accordion,
                        resume_exec_id,
                        generate_btn,
                        approve_btn,
                        edit_approve_btn,
                        reject_btn,
                        resume_btn,
                    ],
                )

                # Wire up approval buttons
                # Note: These must be generator functions (not lambdas) to properly stream updates
                def approve_handler(exec_id: str, resume_url: str):
                    """Handle approve button click."""
                    yield from continue_after_approval(exec_id, resume_url, "approve")

                def edit_approve_handler(exec_id: str, resume_url: str, edited: str):
                    """Handle edit+approve button click."""
                    yield from continue_after_approval(exec_id, resume_url, "edit", edited)

                def reject_handler(exec_id: str, resume_url: str):
                    """Handle reject button click."""
                    yield from continue_after_approval(exec_id, resume_url, "reject")

                approve_btn.click(
                    fn=approve_handler,
                    inputs=[execution_id_state, resume_url_state],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                ).then(
                    fn=update_approval_visibility,
                    inputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                        approval_group,
                        edited_quote_input,
                        resume_accordion,
                        resume_exec_id,
                        generate_btn,
                        approve_btn,
                        edit_approve_btn,
                        reject_btn,
                        resume_btn,
                    ],
                )

                edit_approve_btn.click(
                    fn=edit_approve_handler,
                    inputs=[execution_id_state, resume_url_state, edited_quote_input],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                ).then(
                    fn=update_approval_visibility,
                    inputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                        approval_group,
                        edited_quote_input,
                        resume_accordion,
                        resume_exec_id,
                        generate_btn,
                        approve_btn,
                        edit_approve_btn,
                        reject_btn,
                        resume_btn,
                    ],
                )

                reject_btn.click(
                    fn=reject_handler,
                    inputs=[execution_id_state, resume_url_state],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                ).then(
                    fn=update_approval_visibility,
                    inputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                    ],
                    outputs=[
                        status_box,
                        quote_output,
                        image_output,
                        video_output,
                        execution_id_state,
                        resume_url_state,
                        waiting_for_approval_state,
                        approval_group,
                        edited_quote_input,
                        resume_accordion,
                        resume_exec_id,
                        generate_btn,
                        approve_btn,
                        edit_approve_btn,
                        reject_btn,
                        resume_btn,
                    ],
                )

                gr.Markdown(
                    """
                    ---
                    **Note:** Generation typically takes 3-5 minutes.
                    - **Custom Quote**: Optional - provide your own quote or leave empty
                      for AI generation
                    - **Quote generation**: ~5 seconds (Claude Sonnet 4.5) - skipped if
                      custom quote provided
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
