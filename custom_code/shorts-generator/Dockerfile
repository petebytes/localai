# Multi-stage build for shorts-generator
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY *.py ./
COPY tests ./tests

# Production stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/*.py ./

# Create downloads directory
RUN mkdir -p downloads

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 7860 8000

# Run unified launcher
CMD ["python", "app.py"]
