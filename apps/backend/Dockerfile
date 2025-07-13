FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Copy dependency definition files first for better caching
COPY pyproject.toml uv.lock ./

# Install only runtime dependencies (skip dev extras)
RUN uv sync --system --no-dev

# Copy backend source code
COPY apps/backend /app/apps/backend

# Start the FastAPI server via uv
CMD ["uv", "run", "uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
