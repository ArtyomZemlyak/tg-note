FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    git \
    curl \
    ca-certificates \
    pkg-config \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# Ensure python alias and install pip tooling
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    python -m ensurepip && \
    python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
COPY docker/docling-mcp/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY docker/docling-mcp/app /opt/docling-mcp/app
COPY docker/docling-mcp/docker-entrypoint.sh /usr/local/bin/entrypoint.sh

# Create runtime directories
RUN mkdir -p /opt/docling-mcp/config \
    /opt/docling-mcp/models \
    /opt/docling-mcp/logs \
    /opt/docling-mcp/cache && \
    chmod +x /usr/local/bin/entrypoint.sh

# Environment configuration
ENV PYTHONPATH="/opt/docling-mcp/app:${PYTHONPATH}" \
    DOCLING_CONFIG_PATH=/opt/docling-mcp/config/docling-config.json \
    DOCLING_MODELS_DIR=/opt/docling-mcp/models \
    DOCLING_LOG_DIR=/opt/docling-mcp/logs \
    DOCLING_CACHE_DIR=/opt/docling-mcp/cache \
    HF_HOME=/opt/docling-mcp/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /opt/docling-mcp

VOLUME ["/opt/docling-mcp/config", "/opt/docling-mcp/models", "/opt/docling-mcp/logs", "/opt/docling-mcp/cache"]

EXPOSE 8077

ENTRYPOINT ["entrypoint.sh"]
CMD ["run"]
