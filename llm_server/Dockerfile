# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
ENV PYSETUP_PATH="/app"
WORKDIR $PYSETUP_PATH

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN uv sync --locked --no-install-project

# Copy application code
COPY . .

# Create cache directory for HuggingFace models
RUN mkdir -p /app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

# Activate venv by default
ENV VIRTUAL_ENV=$PYSETUP_PATH/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log_conf.yaml"]
