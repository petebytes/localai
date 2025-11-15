"""n8n API client for triggering workflows and retrieving execution data."""

import os
import sys
from typing import Any, cast

from httpx import AsyncClient

from models import (
    DEFAULT_IMAGE_PROMPT,
    DEFAULT_QUOTE_PROMPT,
    ApprovalAction,
    ExecutionStatus,
    GenerateRequest,
    GenerateResponse,
    QuoteApprovalRequest,
)


class N8nError(Exception):
    """Exception raised for n8n API errors."""

    pass


class N8nClient:
    """Client for interacting with n8n API."""

    def __init__(
        self,
        base_url: str,
        webhook_path: str = "/webhook/shorts-generate",
        api_key: str | None = None,
    ) -> None:
        """Initialize n8n client.

        Args:
            base_url: Base URL of n8n instance (e.g., http://n8n:5678)
            webhook_path: Webhook path to trigger (e.g., /webhook/shorts-generate)
            api_key: n8n API key for authentication (required for API endpoints)
        """
        self.base_url = base_url.rstrip("/")
        self.webhook_path = webhook_path
        self.api_key = api_key
        self._client: AsyncClient | None = None

    async def __aenter__(self) -> "N8nClient":
        """Enter async context manager."""
        self._client = AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> AsyncClient:
        """Get HTTP client, creating if needed."""
        if self._client is None:
            self._client = AsyncClient(timeout=30.0)
        return self._client

    async def trigger_workflow(self, request: GenerateRequest) -> str:
        """Trigger n8n workflow via webhook with hardcoded prompts.

        Args:
            request: Generate request with optional custom quote

        Returns:
            Execution ID from webhook response

        Raises:
            N8nError: If workflow trigger fails
        """
        client = self._get_client()

        url = f"{self.base_url}{self.webhook_path}"
        # Use hardcoded prompts - not exposed to users
        payload = {
            "quote_system_prompt": DEFAULT_QUOTE_PROMPT,
            "image_system_prompt": DEFAULT_IMAGE_PROMPT,
        }

        # Add custom quote if provided
        if request.custom_quote:
            payload["custom_quote"] = request.custom_quote

        response = await client.post(url, json=payload)

        if response.status_code not in (200, 201):
            raise N8nError(f"Failed to trigger workflow: {response.status_code} {response.text}")

        # Webhook returns the execution ID in the response
        data: dict[str, Any] = response.json()

        # Try different response formats (webhook with respondToWebhook node)
        execution_id = cast(
            str,
            data.get("executionId")  # Direct from respondToWebhook
            or data.get("data", {}).get("executionId")  # Nested format
            or data.get("workflowData", {}).get("executionId"),  # Alternative format
        )

        if not execution_id:
            raise N8nError(f"No execution ID in webhook response: {data}")

        return str(execution_id)

    async def get_execution_status(self, execution_id: str) -> GenerateResponse:
        """Get status and results of workflow execution.

        Args:
            execution_id: n8n execution ID

        Returns:
            GenerateResponse with current status and results

        Raises:
            N8nError: If status retrieval fails
        """
        client = self._get_client()

        url = f"{self.base_url}/api/v1/executions/{execution_id}?includeData=true"

        # Prepare headers with API key if available
        headers = {}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key

        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise N8nError(
                f"Failed to get execution status: {response.status_code} {response.text}"
            )

        data = response.json()
        return self._parse_execution_response(execution_id, data)

    def _parse_execution_response(
        self, execution_id: str, data: dict[str, Any]
    ) -> GenerateResponse:
        """Parse n8n execution response into GenerateResponse.

        Args:
            execution_id: Execution ID
            data: Raw n8n API response

        Returns:
            Parsed GenerateResponse
        """
        # Check top-level status first (for waiting executions)
        top_level_status = data.get("status")

        # Execution data is nested under "data"
        exec_data = data.get("data", {})

        # Status and finished can be at top level OR in the data object
        status_str = top_level_status or exec_data.get("status", "running")
        finished = data.get("finished", exec_data.get("finished", False))

        # Map n8n status to our ExecutionStatus enum
        if status_str == "waiting":
            status = ExecutionStatus.WAITING_FOR_APPROVAL
        elif status_str == "error":
            status = ExecutionStatus.ERROR
        elif status_str == "success" and finished:
            status = ExecutionStatus.SUCCESS
        elif not finished:
            status = ExecutionStatus.RUNNING
        else:
            status = ExecutionStatus.PENDING

        # Extract error if present
        error = None
        if status == ExecutionStatus.ERROR:
            result_data = exec_data.get("data", {}).get("resultData", {})
            error_data = result_data.get("error", {})
            error = error_data.get("message", "Unknown error")

        # Extract results if successful or waiting for approval
        quote = None
        image_prompt = None
        image_url = None
        video_prompt = None
        video_url = None
        video_path = None

        # For waiting executions, data is at exec_data.resultData
        # For completed executions, data is at exec_data.data.resultData
        resume_url = None
        if status == ExecutionStatus.WAITING_FOR_APPROVAL:
            # Waiting execution - data is at top level of exec_data
            run_data = exec_data.get("resultData", {}).get("runData", {})

            # Construct resume URL from execution ID
            # The Wait node creates a webhook at /webhook-waiting/{execution_id}
            # We need to use the external URL, not the internal n8n:5678 URL
            base_url = self.base_url.replace("http://n8n:5678", os.getenv("N8N_EXTERNAL_URL", "https://n8n.lan"))
            resume_url = f"{base_url}/webhook-waiting/{execution_id}"

            # Extract quote from "Quote writer" or "Format Custom Quote" node
            quote_node = run_data.get("Quote writer", []) or run_data.get("Format Custom Quote", [])
            if quote_node and len(quote_node) > 0:
                quote_output = quote_node[0].get("data", {}).get("main", [[]])[0]
                if quote_output:
                    quote_data = quote_output[0].get("json", {})
                    quote = quote_data.get("output")

        if status == ExecutionStatus.SUCCESS:
            run_data = exec_data.get("data", {}).get("resultData", {}).get("runData", {})

            # Extract quote from "Quote writer" node
            quote_node = run_data.get("Quote writer", [])
            if quote_node and len(quote_node) > 0:
                quote_output = quote_node[0].get("data", {}).get("main", [[]])[0]
                if quote_output:
                    quote = quote_output[0].get("json", {}).get("output")

            # Extract prompts from "Parse Prompts" node (contains both image and video prompts)
            parse_node = run_data.get("Parse Prompts", [])
            if parse_node and len(parse_node) > 0:
                parse_output = parse_node[0].get("data", {}).get("main", [[]])[0]
                if parse_output:
                    parse_data = parse_output[0].get("json", {})
                    image_prompt = parse_data.get("image_prompt")
                    video_prompt = parse_data.get("video_prompt")
                    # Use original_quote if quote wasn't extracted from Quote writer
                    if not quote:
                        quote = parse_data.get("original_quote")

            # Extract image filename from "ComfyUI: Generate Image" node
            image_node = run_data.get("ComfyUI: Generate Image", [])
            if image_node and len(image_node) > 0:
                image_output = image_node[0].get("data", {}).get("main", [[]])[0]
                if image_output:
                    json_data = image_output[0].get("json", {})
                    # Try images array first (old format), then filename directly (new format)
                    images = json_data.get("images", [])
                    if images and images[0].get("filename"):
                        filename = images[0].get("filename")
                    else:
                        filename = json_data.get("filename")

                    if filename:
                        image_url = f"/download/{filename}"

            # Extract video data from "Ovi: Generate Video" node
            video_node = run_data.get("Ovi: Generate Video", [])
            if video_node and len(video_node) > 0:
                video_output = video_node[0].get("data", {}).get("main", [[]])[0]
                if video_output:
                    video_data = video_output[0].get("json", {})
                    video_path = video_data.get("video_path")
                    if video_path:
                        # Extract filename from path for download URL
                        video_filename = os.path.basename(video_path)
                        video_url = f"/download/{video_filename}"

        return GenerateResponse(
            execution_id=execution_id,
            status=status,
            quote=quote,
            image_prompt=image_prompt,
            image_url=image_url,
            video_prompt=video_prompt,
            video_url=video_url,
            video_path=video_path,
            resume_url=resume_url,
            error=error,
        )

    async def approve_quote_with_url(self, request: QuoteApprovalRequest) -> dict[str, bool]:
        """Resume workflow execution with quote approval decision using the actual webhook URL.

        Args:
            request: Quote approval request with action, optional edited quote, and resume_url

        Returns:
            Dict with success status

        Raises:
            N8nError: If approval fails
        """
        import httpx

        # Check environment variable for SSL verification setting
        # Defaults to false since n8n typically uses self-signed certificates
        # Set N8N_VERIFY_SSL=true to enable SSL verification
        verify_ssl = os.getenv("N8N_VERIFY_SSL", "false").lower() == "true"

        async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
            url = request.resume_url
            # Validate URL exists and is not the string "None"
            if not url or url == "None" or not url.startswith(("http://", "https://")):
                raise N8nError("Valid resume URL with http:// or https:// protocol is required for quote approval")

            # Prepare payload based on action
            payload: dict[str, Any] = {"action": request.action.value}

            if request.action == ApprovalAction.EDIT and request.edited_quote:
                payload["approved_quote"] = request.edited_quote
                payload["approved"] = True  # EDIT action also means approved
            elif request.action == ApprovalAction.APPROVE:
                # The workflow will use the original quote
                payload["approved"] = True
            elif request.action == ApprovalAction.REJECT:
                payload["approved"] = False

            response = await client.post(url, json=payload)

            if response.status_code not in (200, 201, 204):
                raise N8nError(f"Failed to approve quote: {response.status_code} {response.text}")

            return {"success": True}

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
