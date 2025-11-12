"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from models import ExecutionStatus, GenerateRequest, GenerateResponse


def test_generate_request_creation() -> None:
    """Test GenerateRequest can be created."""
    request = GenerateRequest()

    # Request should be valid with no user-facing fields
    assert request is not None


def test_generate_response_pending_status() -> None:
    """Test GenerateResponse for pending execution."""
    response = GenerateResponse(
        execution_id="exec_123",
        status=ExecutionStatus.PENDING,
    )

    assert response.execution_id == "exec_123"
    assert response.status == ExecutionStatus.PENDING
    assert response.quote is None
    assert response.image_prompt is None
    assert response.image_url is None
    assert response.error is None


def test_generate_response_running_status() -> None:
    """Test GenerateResponse for running execution."""
    response = GenerateResponse(
        execution_id="exec_123",
        status=ExecutionStatus.RUNNING,
    )

    assert response.status == ExecutionStatus.RUNNING
    assert response.quote is None


def test_generate_response_success_status() -> None:
    """Test GenerateResponse for successful execution."""
    response = GenerateResponse(
        execution_id="exec_123",
        status=ExecutionStatus.SUCCESS,
        quote="Healing is not linear",
        image_prompt="A winding path through a peaceful forest",
        image_url="/download/hidream_test_00001.png",
    )

    assert response.status == ExecutionStatus.SUCCESS
    assert response.quote == "Healing is not linear"
    assert response.image_prompt == "A winding path through a peaceful forest"
    assert response.image_url == "/download/hidream_test_00001.png"
    assert response.error is None


def test_generate_response_error_status() -> None:
    """Test GenerateResponse for failed execution."""
    response = GenerateResponse(
        execution_id="exec_123",
        status=ExecutionStatus.ERROR,
        error="ComfyUI timeout",
    )

    assert response.status == ExecutionStatus.ERROR
    assert response.error == "ComfyUI timeout"
    assert response.quote is None


def test_generate_response_requires_execution_id() -> None:
    """Test GenerateResponse requires execution_id."""
    with pytest.raises(ValidationError):
        GenerateResponse(status=ExecutionStatus.PENDING)  # type: ignore[call-arg]


def test_execution_status_enum_values() -> None:
    """Test ExecutionStatus enum has expected values."""
    assert ExecutionStatus.PENDING.value == "pending"
    assert ExecutionStatus.RUNNING.value == "running"
    assert ExecutionStatus.SUCCESS.value == "success"
    assert ExecutionStatus.ERROR.value == "error"


def get_mock_request() -> GenerateRequest:
    """Factory for creating test GenerateRequest instances."""
    return GenerateRequest()


def get_mock_response(overrides: dict[str, object] | None = None) -> GenerateResponse:
    """Factory for creating test GenerateResponse instances."""
    defaults = {
        "execution_id": "test_exec_123",
        "status": ExecutionStatus.SUCCESS,
        "quote": "Test quote",
        "image_prompt": "Test image prompt",
        "image_url": "/download/test.png",
    }
    if overrides:
        defaults.update(overrides)  # type: ignore[arg-type]
    return GenerateResponse(**defaults)  # type: ignore[arg-type]
