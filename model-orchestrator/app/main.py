"""
Model Orchestrator Service

Manages GPU memory and model lifecycle across multiple AI services.
Provides explicit load/unload control for n8n workflows.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

import httpx
import pynvml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelLoadRequest(BaseModel):
    """Request to load a model"""
    model: str = Field(..., description="Model identifier (e.g., 'qwen3-vl-30b', 'whisperx')")
    service: str = Field(..., description="Service name (e.g., 'llama-cpp', 'whisperx')")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1=low, 10=high)")


class ModelUnloadRequest(BaseModel):
    """Request to unload a model"""
    model: str = Field(..., description="Model identifier")
    force: bool = Field(default=False, description="Force unload even if in use")


class ModelInfo(BaseModel):
    """Information about a loaded model"""
    model: str
    service: str
    loaded_at: str
    vram_mb: Optional[int] = None
    status: str


class GPUStatus(BaseModel):
    """GPU memory status"""
    total_mb: int
    used_mb: int
    free_mb: int
    utilization_percent: float
    loaded_models: Dict[str, ModelInfo]


class ModelOrchestrator:
    """Manages model lifecycle and GPU memory"""

    def __init__(self):
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.service_endpoints = {
            "llama-cpp": "http://llama-cpp:8000",
            "whisperx": "http://whisperx:8000",
            "ovi": "http://ovi:8300",
            "infinitetalk": "http://infinitetalk:8200",
            "wan": "http://wan:7860",
        }
        self.http_client: Optional[httpx.AsyncClient] = None

        # Initialize NVML for GPU monitoring
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            logger.info("NVML initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NVML: {e}")
            self.gpu_handle = None

    async def startup(self):
        """Initialize async resources"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Model Orchestrator started")

    async def shutdown(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()
        if self.gpu_handle:
            pynvml.nvmlShutdown()
        logger.info("Model Orchestrator shutdown")

    def get_gpu_memory(self) -> tuple[int, int, int]:
        """Get GPU memory usage in MB"""
        if not self.gpu_handle:
            return 0, 0, 0

        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            total_mb = info.total // (1024 * 1024)
            used_mb = info.used // (1024 * 1024)
            free_mb = info.free // (1024 * 1024)
            return total_mb, used_mb, free_mb
        except Exception as e:
            logger.error(f"Failed to get GPU memory: {e}")
            return 0, 0, 0

    def get_gpu_utilization(self) -> float:
        """Get GPU utilization percentage"""
        if not self.gpu_handle:
            return 0.0

        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            return float(util.gpu)
        except Exception as e:
            logger.error(f"Failed to get GPU utilization: {e}")
            return 0.0

    async def load_model(self, request: ModelLoadRequest) -> ModelInfo:
        """Load a model into GPU memory"""

        # Check if already loaded
        if request.model in self.loaded_models:
            logger.info(f"Model {request.model} already loaded")
            return self.loaded_models[request.model]

        # Get current GPU memory
        total_mb, used_mb, free_mb = self.get_gpu_memory()
        logger.info(f"GPU Memory - Total: {total_mb}MB, Used: {used_mb}MB, Free: {free_mb}MB")

        # For llama-cpp, model loads on container start - just verify it's ready
        if request.service == "llama-cpp":
            endpoint = self.service_endpoints.get(request.service)
            if not endpoint:
                raise HTTPException(status_code=400, detail=f"Unknown service: {request.service}")

            try:
                response = await self.http_client.get(f"{endpoint}/health", timeout=5.0)
                if response.status_code == 200:
                    model_info = ModelInfo(
                        model=request.model,
                        service=request.service,
                        loaded_at=datetime.utcnow().isoformat(),
                        status="loaded"
                    )
                    self.loaded_models[request.model] = model_info
                    logger.info(f"Model {request.model} verified loaded in {request.service}")
                    return model_info
                else:
                    raise HTTPException(status_code=503, detail=f"Service {request.service} not ready")
            except httpx.RequestError as e:
                logger.error(f"Failed to verify {request.service}: {e}")
                raise HTTPException(status_code=503, detail=f"Service {request.service} not reachable")

        # For other services, they auto-load on first request
        # Just track that we expect them to be loaded
        model_info = ModelInfo(
            model=request.model,
            service=request.service,
            loaded_at=datetime.utcnow().isoformat(),
            status="loading"
        )
        self.loaded_models[request.model] = model_info
        logger.info(f"Model {request.model} marked for loading in {request.service}")

        return model_info

    async def unload_model(self, request: ModelUnloadRequest) -> dict:
        """Unload a model from GPU memory"""

        if request.model not in self.loaded_models:
            logger.warning(f"Model {request.model} not tracked as loaded")
            return {"status": "not_loaded", "model": request.model}

        model_info = self.loaded_models[request.model]
        service = model_info.service

        # For llama-cpp, we need to stop the container to free VRAM
        # This will be handled by Docker orchestration
        if service == "llama-cpp":
            logger.info(f"To unload {request.model}, stop the llama-cpp container")
            # Note: We don't actually stop the container here - that's done via Docker
            # This is just tracking state
            del self.loaded_models[request.model]
            return {
                "status": "unload_requested",
                "model": request.model,
                "service": service,
                "note": "Stop llama-cpp container to fully free VRAM"
            }

        # For other services, we just remove from tracking
        # They'll unload on their own when idle or explicitly via their APIs
        del self.loaded_models[request.model]
        logger.info(f"Model {request.model} removed from tracking")

        return {
            "status": "unloaded",
            "model": request.model,
            "service": service
        }

    def get_status(self) -> GPUStatus:
        """Get current GPU and model status"""
        total_mb, used_mb, free_mb = self.get_gpu_memory()
        utilization = self.get_gpu_utilization()

        return GPUStatus(
            total_mb=total_mb,
            used_mb=used_mb,
            free_mb=free_mb,
            utilization_percent=utilization,
            loaded_models=self.loaded_models
        )


# Global orchestrator instance
orchestrator = ModelOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    await orchestrator.startup()
    yield
    await orchestrator.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Model Orchestrator",
    description="Manages GPU memory and model lifecycle for LocalAI services",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "model-orchestrator"}


@app.get("/models/status", response_model=GPUStatus)
async def get_model_status():
    """Get current GPU memory usage and loaded models"""
    return orchestrator.get_status()


@app.post("/models/load", response_model=ModelInfo)
async def load_model(request: ModelLoadRequest):
    """
    Load a model into GPU memory.

    For llama-cpp, verifies the service is ready.
    For other services, marks the model for lazy loading.
    """
    return await orchestrator.load_model(request)


@app.post("/models/unload")
async def unload_model(request: ModelUnloadRequest):
    """
    Unload a model from GPU memory.

    Note: For llama-cpp, you must stop the container to fully free VRAM.
    """
    return await orchestrator.unload_model(request)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Model Orchestrator",
        "version": "1.0.0",
        "endpoints": {
            "status": "/models/status",
            "load": "POST /models/load",
            "unload": "POST /models/unload",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
