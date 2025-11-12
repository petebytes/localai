"""Tests for FastAPI endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from api import app, get_n8n_client
from models import ExecutionStatus, GenerateResponse
from n8n_client import N8nError


class MockN8nClient:
    """Mock n8n client for testing."""

    def __init__(self) -> None:
        self.triggered = False
        self.execution_id = "test_exec_123"

    async def trigger_workflow(self, request: object) -> str:
        """Mock trigger workflow."""
        self.triggered = True
        return self.execution_id

    async def get_execution_status(self, execution_id: str) -> GenerateResponse:
        """Mock get execution status."""
        return GenerateResponse(
            execution_id=execution_id,
            status=ExecutionStatus.SUCCESS,
            quote="Test quote",
            image_prompt="Test prompt",
            image_url="/download/test.png",
        )

    async def close(self) -> None:
        """Mock close."""
        pass


@pytest.fixture
def mock_n8n_client() -> MockN8nClient:
    """Create mock n8n client."""
    return MockN8nClient()


@pytest.fixture
def client(mock_n8n_client: MockN8nClient) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    app.dependency_overrides[get_n8n_client] = lambda: mock_n8n_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "n8n_url" in data


def test_generate_endpoint(
    client: TestClient,
    mock_n8n_client: MockN8nClient,
) -> None:
    """Test generate endpoint."""
    response = client.post("/api/generate", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == "test_exec_123"
    assert data["status"] in ["pending", "running"]
    assert mock_n8n_client.triggered


def test_status_endpoint(client: TestClient) -> None:
    """Test status endpoint returns execution status."""
    response = client.get("/api/status/test_exec_123")

    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == "test_exec_123"
    assert data["status"] == "success"
    assert data["quote"] == "Test quote"
    assert data["image_prompt"] == "Test prompt"
    assert data["image_url"] == "/download/test.png"


def test_status_endpoint_not_found(client: TestClient, mocker: MockerFixture) -> None:
    """Test status endpoint handles non-existent execution."""
    mock_client = MockN8nClient()

    async def mock_get_status(execution_id: str) -> GenerateResponse:
        raise N8nError("Execution not found")

    mocker.patch.object(mock_client, "get_execution_status", side_effect=mock_get_status)

    app.dependency_overrides[get_n8n_client] = lambda: mock_client
    test_client = TestClient(app)

    response = test_client.get("/api/status/invalid_id")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


def test_download_endpoint_file_exists(client: TestClient, mocker: MockerFixture) -> None:
    """Test download endpoint serves existing file."""
    from pathlib import Path

    mock_path = mocker.MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.is_file.return_value = True
    mock_path.__str__.return_value = "/fake/path/test.png"

    mocker.patch("api.COMFYUI_OUTPUT_PATH", Path("/fake/path"))
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.is_file", return_value=True)

    # Note: FileResponse will try to open file, so we need a real temp file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(b"fake image data")
        tmp_path = tmp.name

    mocker.patch("api.COMFYUI_OUTPUT_PATH", Path(tempfile.gettempdir()))

    response = client.get(f"/api/download/{Path(tmp_path).name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Cleanup
    Path(tmp_path).unlink()


def test_download_endpoint_file_not_found(client: TestClient, mocker: MockerFixture) -> None:
    """Test download endpoint returns 404 for missing file."""
    from pathlib import Path

    mocker.patch("api.COMFYUI_OUTPUT_PATH", Path("/fake/nonexistent"))

    response = client.get("/api/download/nonexistent.png")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
