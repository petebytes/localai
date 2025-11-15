# syntax=docker/dockerfile:1.12
# WhisperX Docker Image - Flexible CUDA Version Testing with BuildKit Cache Optimization
#
# QUICK TEST DIFFERENT CUDA VERSIONS:
#   docker compose build --build-arg CUDA_VERSION=12.8 whisperx
#   docker compose build --build-arg CUDA_VERSION=13.0 whisperx
#   docker compose build --build-arg CUDA_VERSION=12.1 whisperx
#
# SUPPORTED CUDA VERSIONS:
#   12.1 = Legacy stable (older GPUs)
#   12.8 = RTX 5090 RECOMMENDED ✅ (Blackwell - PyTorch 2.7.1+cu128 official)
#   12.9 = NOT SUPPORTED ❌ (no PyTorch cu129 wheels, falls back to cu126)
#   13.0 = NOT SUPPORTED ❌ (no PyTorch cu130 wheels, falls back to cu126)
#   13.1 = Experimental (wait for PyTorch 2.8+ support)
#
# RTX 5090 Testing Results (Oct 2025):
#   ✅ CUDA 12.8: Works perfectly (2.52s, 17.86% WER)
#   ❌ CUDA 12.9/13.0: Kernel error - PyTorch version mismatch
#
# Build base images first: ./scripts/build-cuda-base.sh all-versions

ARG CUDA_VERSION=12.8
# Use official NVIDIA CUDA runtime with cuDNN
FROM nvidia/cuda:${CUDA_VERSION}.0-cudnn-runtime-ubuntu22.04

LABEL maintainer="Local AI Packaged"
LABEL description="WhisperX transcription service - flexible CUDA testing"
LABEL service.type="transcription"

# Install Python 3.10, pip, ffmpeg, and other dependencies
RUN apt-get update -y && \
    apt-get install -y \
    python3.10 python3.10-dev python3-pip \
    ffmpeg git wget curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install PyTorch 2.8.0 with CUDA 12.8 support
# torchaudio 2.8.0 required for WhisperX compatibility (2.9+ breaks AudioMetaData)
RUN --mount=type=cache,id=pip-cache-shared,target=/root/.cache/pip,sharing=shared \
    pip3 install --index-url https://download.pytorch.org/whl/cu128 \
    'torch==2.8.0+cu128' 'torchvision==0.23.0+cu128' 'torchaudio==2.8.0+cu128'

# Set cache environment variables for persistent model storage
ENV HF_HOME=/data/.huggingface
ENV TRANSFORMERS_CACHE=/data/.huggingface/transformers
ENV TORCH_HOME=/data/.torch

# Install WhisperX from git with cache mount - pinned to v3.7.2 (last working version)
# v3.7.2 (Oct 12, 2024) is compatible with transformers 4.57.1 and PyTorch 2.7.1
# Later versions have breaking changes with Pipeline imports
# Use shared cache ID to share pip cache with Kokoro and other services
RUN --mount=type=cache,id=pip-cache-shared,target=/root/.cache/pip,sharing=shared \
    pip3 install "git+https://github.com/m-bain/whisperx.git@v3.7.2"

# Install FastAPI and related web server dependencies with cache mount
RUN --mount=type=cache,id=pip-cache-shared,target=/root/.cache/pip,sharing=shared \
    pip3 install \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    python-multipart==0.0.6 \
    pydantic==2.5.3

# Create application directories including cache directories
RUN mkdir -p /app/uploads /root/.cache /data/.huggingface /data/.torch /app/shared/temp /app/shared/input /app/shared/output

WORKDIR /app

# Copy application code LAST (changes most frequently)
COPY api_server.py /app/api_server.py
COPY ffmpeg_processor.py /app/ffmpeg_processor.py
COPY video_segmenter.py /app/video_segmenter.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["python3", "-u", "api_server.py"]
