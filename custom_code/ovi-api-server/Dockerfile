# Ovi API Server - FastAPI wrapper for Ovi video+audio generation
# Shares base environment with Ovi Gradio app

FROM localai-ovi:latest

# Metadata
LABEL maintainer="LocalAI Platform"
LABEL description="Ovi API Server - REST API for Ovi 11B video+audio generation"
LABEL version="1.0.0"

# Install FastAPI dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.3 \
    python-multipart==0.0.20

# Copy API server code
COPY ovi_api_server/ /app/ovi_api_server/

# Set Python path to include both ovi and API server
ENV PYTHONPATH="/workspace/ovi:/app:${PYTHONPATH}"

# Set working directory to match Ovi base image (for relative path config loading)
WORKDIR /workspace/ovi

# Environment variables (can be overridden in docker-compose.yml)
ENV OVI_DIR=/workspace/ovi
ENV OVI_CPU_OFFLOAD=true
ENV OVI_FP8=false
ENV OVI_QINT8=false
ENV OVI_OUTPUT_DIR=/output
ENV PORT=8300
ENV HOST=0.0.0.0

# Expose API port
EXPOSE 8300

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8300/api/health || exit 1

# Run FastAPI server
CMD ["python3", "-m", "uvicorn", "ovi_api_server.main:app", "--host", "0.0.0.0", "--port", "8300"]
