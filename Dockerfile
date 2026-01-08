# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

ENV PYSETUP_PATH="/usr/src/app"

WORKDIR $PYSETUP_PATH

# Copy application code
COPY . .

# Install dependencies using uv
RUN uv sync --locked --no-install-project

# Activate venv by default in shell (optional but nice)
ENV VIRTUAL_ENV=$PYSETUP_PATH/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
