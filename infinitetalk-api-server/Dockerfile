# syntax=docker/dockerfile:1.12
# InfiniteTalk API Server - FastAPI wrapper for automated video generation
#
# This service provides a REST API for generating talking head videos
# Uses shared cuda-base image and mounts InfiniteTalk source from volume
#
# Build base images first: ./scripts/build-cuda-base.sh all-versions

ARG CUDA_VERSION=12.8
FROM cuda-base:runtime-${CUDA_VERSION}

LABEL maintainer="Local AI Packaged"
LABEL description="InfiniteTalk API Server - REST API for automated video generation"
LABEL service.type="video-generation-api"

# Metadata - base image provides CUDA 12.8 + PyTorch 2.9.0 + common deps
# Base includes: python3.10, pip, ffmpeg, git, numpy, requests, PyTorch

# Set cache environment variables for persistent model storage
ENV HF_HOME=/data/.huggingface
ENV TRANSFORMERS_CACHE=/data/.huggingface/transformers
ENV TORCH_HOME=/data/.torch

# Set working directory for API server
WORKDIR /app

# Install build tools, CUDA development libraries, Python headers, and uv package manager
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cuda-cudart-dev-12-8 \
    python3.10-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Create Python 3.10 virtual environment using uv
RUN uv venv -p 3.10 /opt/venv

# Activate venv by adding to PATH
ENV PATH="/opt/venv/bin:${PATH}"

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies using uv with explicit CUDA 12.8 backend (RTX 5090 optimization)
# vllm and flashinfer-python are critical for RTX 5090 performance
RUN --mount=type=cache,id=uv-cache-shared,target=/root/.cache/uv,sharing=shared \
    uv pip install vllm flashinfer-python --torch-backend=cu128 && \
    uv pip install -r requirements.txt --torch-backend=cu128

# Copy API server code
COPY infinitetalk_api_server/ ./infinitetalk_api_server/

# Create output directory
RUN mkdir -p /output && chmod 777 /output

# Fix Triton CUDA kernel compilation
# Triton needs libcuda.so.1 symlink in stubs directory for gcc linking
# Add stubs to ldconfig so Triton's libcuda_dirs() can find it
RUN cd /usr/local/cuda-12.8/targets/x86_64-linux/lib/stubs && \
    ln -sf libcuda.so libcuda.so.1 && \
    echo '/usr/local/cuda-12.8/targets/x86_64-linux/lib/stubs' > /etc/ld.so.conf.d/cuda-stubs.conf && \
    ldconfig

# Expose API port
EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8200/api/health || exit 1

# Set environment variables
# PYTHONPATH includes /workspace which will be mounted from InfiniteTalk volume
# LD_LIBRARY_PATH includes both NVIDIA driver libs (for PyTorch) and CUDA compat libs (for Triton)
ENV PYTHONPATH="/workspace:/app:${PYTHONPATH}" \
    INFINITETALK_DIR="/workspace" \
    HOST=0.0.0.0 \
    PORT=8200 \
    LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/local/cuda-12.8/compat:${LD_LIBRARY_PATH}"

# Run with uvicorn
CMD ["python3", "-m", "uvicorn", "infinitetalk_api_server.main:app", "--host", "0.0.0.0", "--port", "8200"]
