# llama.cpp for RTX 5090 Blackwell - Using cuBLAS for stability
# Based on community testing: Blackwell sm_120 requires cuBLAS instead of custom kernels
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    curl \
    python3 \
    python3-pip \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone llama.cpp
WORKDIR /app
RUN git clone https://github.com/ggerganov/llama.cpp.git

# Build llama.cpp with CUDA support for RTX 5090 Blackwell
# CRITICAL for RTX 5090: Use runtime env var GGML_CUDA_FORCE_CUBLAS=1 to avoid kernel issues
# CMAKE_CUDA_ARCHITECTURES=native will detect sm_120 for Blackwell
WORKDIR /app/llama.cpp

# Use CUDA stub libraries during build to avoid linking issues
RUN ln -sf /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 && \
    export LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH && \
    cmake -B build \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DGGML_NATIVE=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --config Release -j$(nproc)

# Runtime image
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libcurl4-openssl-dev \
    libgomp1 \
    libcublas-12-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy built binaries from builder
COPY --from=builder /app/llama.cpp/build/bin /app/llama.cpp/build/bin

# Install Python dependencies for model downloading
RUN pip3 install --no-cache-dir \
    huggingface-hub \
    requests

# Create directory for shared HuggingFace cache
RUN mkdir -p /data/.huggingface

# Copy startup script
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set working directory
WORKDIR /app/llama.cpp

# Environment variables
ENV MODEL_PATH=/data/.huggingface/hub/models--Qwen--Qwen3-VL-30B-A3B-Instruct-GGUF/snapshots/latest/qwen3-vl-30b-a3b-instruct-q4_k_m.gguf
ENV HOST=0.0.0.0
ENV PORT=8000
ENV CONTEXT_SIZE=8192
ENV N_GPU_LAYERS=99
ENV HF_HOME=/data/.huggingface
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
# Force cuBLAS for RTX 5090 stability
ENV GGML_CUDA_FORCE_CUBLAS=1
ENV CUDA_VISIBLE_DEVICES=0

EXPOSE 8000

CMD ["/app/start.sh"]