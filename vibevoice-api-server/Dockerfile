# syntax=docker/dockerfile:1.12
# VibeVoice API Server Dockerfile with CUDA support
#
# Build base images first: ./scripts/build-cuda-base.sh all-versions

ARG CUDA_VERSION=12.8
FROM nvidia/cuda:${CUDA_VERSION}.0-cudnn-runtime-ubuntu22.04

LABEL maintainer="Local AI Packaged"
LABEL description="VibeVoice TTS API with voice cloning and multi-speaker support"
LABEL service.type="text-to-speech"

# Install Python 3.10, pip, ffmpeg, and other dependencies
RUN apt-get update -y && \
    apt-get install -y \
    python3.10 python3.10-dev python3-pip \
    ffmpeg git wget curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install PyTorch 2.8.0 with CUDA 12.8 support
RUN --mount=type=cache,id=pip-cache-shared,target=/root/.cache/pip,sharing=shared \
    pip3 install --index-url https://download.pytorch.org/whl/cu128 \
    'torch==2.8.0+cu128' 'torchvision==0.23.0+cu128' 'torchaudio==2.8.0+cu128'

# Set cache environment variables for persistent model storage
ENV HF_HOME=/data/.huggingface
ENV TRANSFORMERS_CACHE=/data/.huggingface/transformers
ENV TORCH_HOME=/data/.torch

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache mount
# Use shared cache ID to share pip cache with WhisperX, Kokoro and other services
RUN --mount=type=cache,id=pip-cache-shared,target=/root/.cache/pip,sharing=shared \
    pip3 install -r requirements.txt

# Copy application code
COPY vibevoice_api_server/ ./vibevoice_api_server/
COPY vvembed/ ./vvembed/
COPY templates/ ./templates/

# Create output directory
RUN mkdir -p /output

# Expose API port
EXPOSE 8100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8100/api/health || exit 1

# Set environment variables (will be overridden by docker-compose)
ENV MODELS_DIR=/workspace/ComfyUI/models/vibevoice \
    HOST=0.0.0.0 \
    PORT=8100 \
    HF_HOME=/data/.huggingface \
    TORCH_HOME=/data/.torch

# Run the application
CMD ["python3", "-m", "uvicorn", "vibevoice_api_server.main:app", "--host", "0.0.0.0", "--port", "8100"]
