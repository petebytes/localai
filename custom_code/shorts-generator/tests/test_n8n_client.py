"""Tests for n8n API client."""

import pytest
from httpx import AsyncClient, Response
from pytest_mock import MockerFixture

from models import DEFAULT_IMAGE_PROMPT, DEFAULT_QUOTE_PROMPT, ExecutionStatus, GenerateRequest
from n8n_client import N8nClient, N8nError


@pytest.fixture
def n8n_client() -> N8nClient:
    """Create test n8n client."""
    return N8nClient(
        base_url="http://n8n:5678",
        webhook_path="/webhook/shorts-generate",
        api_key="test_api_key",
    )


@pytest.fixture
def mock_request() -> GenerateRequest:
    """Create mock generate request."""
    return GenerateRequest()


async def test_trigger_workflow_success(
    n8n_client: N8nClient,
    mock_request: GenerateRequest,
    mocker: MockerFixture,
) -> None:
    """Test successful workflow trigger."""
    mock_response = {
        "data": {
            "executionId": "exec_123",
        }
    }

    mock_post = mocker.patch.object(
        AsyncClient,
        "post",
        return_value=Response(200, json=mock_response),
    )

    execution_id = await n8n_client.trigger_workflow(mock_request)

    assert execution_id == "exec_123"
    mock_post.assert_called_once()


async def test_trigger_workflow_sends_hardcoded_prompts(
    n8n_client: N8nClient,
    mocker: MockerFixture,
) -> None:
    """Test workflow trigger sends hardcoded default prompts."""
    request = GenerateRequest()

    mock_response = {"data": {"executionId": "exec_456"}}
    mock_post = mocker.patch.object(
        AsyncClient,
        "post",
        return_value=Response(200, json=mock_response),
    )

    execution_id = await n8n_client.trigger_workflow(request)

    assert execution_id == "exec_456"

    # Verify hardcoded default prompts were sent
    call_args = mock_post.call_args
    assert call_args is not None
    json_data = call_args.kwargs.get("json", {})
    assert json_data.get("quote_system_prompt") == DEFAULT_QUOTE_PROMPT
    assert json_data.get("image_system_prompt") == DEFAULT_IMAGE_PROMPT


async def test_trigger_workflow_api_error(
    n8n_client: N8nClient,
    mock_request: GenerateRequest,
    mocker: MockerFixture,
) -> None:
    """Test workflow trigger handles API errors."""
    mocker.patch.object(
        AsyncClient,
        "post",
        return_value=Response(500, json={"error": "Server error"}),
    )

    with pytest.raises(N8nError, match="Failed to trigger workflow"):
        await n8n_client.trigger_workflow(mock_request)


async def test_get_execution_status_sends_api_key(
    mocker: MockerFixture,
) -> None:
    """Test that API key is sent in request headers."""
    client = N8nClient(
        base_url="http://n8n:5678",
        webhook_path="/webhook/shorts-generate",
        api_key="test_key_123",
    )

    mock_response = {
        "data": {
            "id": "exec_123",
            "status": "running",
            "finished": False,
        }
    }

    mock_get = mocker.patch.object(
        AsyncClient,
        "get",
        return_value=Response(200, json=mock_response),
    )

    await client.get_execution_status("exec_123")

    # Verify API key header was sent
    call_args = mock_get.call_args
    assert call_args is not None
    headers = call_args.kwargs.get("headers", {})
    assert headers.get("X-N8N-API-KEY") == "test_key_123"


async def test_get_execution_status_pending(
    n8n_client: N8nClient,
    mocker: MockerFixture,
) -> None:
    """Test getting pending execution status."""
    mock_response = {
        "data": {
            "id": "exec_123",
            "status": "running",
            "finished": False,
        }
    }

    mocker.patch.object(
        AsyncClient,
        "get",
        return_value=Response(200, json=mock_response),
    )

    response = await n8n_client.get_execution_status("exec_123")

    assert response.execution_id == "exec_123"
    assert response.status == ExecutionStatus.RUNNING
    assert response.quote is None
    assert response.image_prompt is None


async def test_get_execution_status_success(
    n8n_client: N8nClient,
    mocker: MockerFixture,
) -> None:
    """Test getting successful execution with results."""
    mock_response = {
        "data": {
            "id": "exec_123",
            "status": "success",
            "finished": True,
            "data": {
                "resultData": {
                    "runData": {
                        "Quote writer": [
                            {"data": {"main": [[{"json": {"output": "Healing is not linear"}}]]}}
                        ],
                        "Quote Image Prompt Generator": [
                            {"data": {"main": [[{"json": {"output": "A winding forest path"}}]]}}
                        ],
                        "ComfyUI: Generate Image": [
                            {
                                "data": {
                                    "main": [
                                        [
                                            {
                                                "json": {
                                                    "images": [
                                                        {"filename": "hidream_test_00001.png"}
                                                    ]
                                                }
                                            }
                                        ]
                                    ]
                                }
                            }
                        ],
                    }
                }
            },
        }
    }

    mocker.patch.object(
        AsyncClient,
        "get",
        return_value=Response(200, json=mock_response),
    )

    response = await n8n_client.get_execution_status("exec_123")

    assert response.execution_id == "exec_123"
    assert response.status == ExecutionStatus.SUCCESS
    assert response.quote == "Healing is not linear"
    assert response.image_prompt == "A winding forest path"
    assert response.image_url == "/download/hidream_test_00001.png"


async def test_get_execution_status_error(
    n8n_client: N8nClient,
    mocker: MockerFixture,
) -> None:
    """Test getting failed execution status."""
    mock_response = {
        "data": {
            "id": "exec_123",
            "status": "error",
            "finished": True,
            "stoppedAt": "2025-11-11T12:00:00.000Z",
            "data": {"resultData": {"error": {"message": "ComfyUI timeout"}}},
        }
    }

    mocker.patch.object(
        AsyncClient,
        "get",
        return_value=Response(200, json=mock_response),
    )

    response = await n8n_client.get_execution_status("exec_123")

    assert response.execution_id == "exec_123"
    assert response.status == ExecutionStatus.ERROR
    assert response.error == "ComfyUI timeout"


async def test_get_execution_status_api_error(
    n8n_client: N8nClient,
    mocker: MockerFixture,
) -> None:
    """Test execution status handles API errors."""
    mocker.patch.object(
        AsyncClient,
        "get",
        return_value=Response(404, json={"error": "Not found"}),
    )

    with pytest.raises(N8nError, match="Failed to get execution status"):
        await n8n_client.get_execution_status("exec_invalid")


async def test_client_context_manager(n8n_client: N8nClient) -> None:
    """Test client can be used as async context manager."""
    async with n8n_client as client:
        assert client is not None
        assert isinstance(client, N8nClient)
