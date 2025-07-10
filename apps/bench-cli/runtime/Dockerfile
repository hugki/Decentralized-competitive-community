FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install PyTorch CPU-only first
RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

# Install ML dependencies
RUN uv pip install --system transformers datasets

# Copy evaluation script
COPY ../run_eval.py /workspace/run_eval.py
WORKDIR /workspace
ENTRYPOINT ["python", "/workspace/run_eval.py"]
