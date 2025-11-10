# AICODE-NOTE: Base PyTorch image with CUDA 12.6 support
# PyTorch, torchvision, and torchaudio are pre-installed in the base image
# Updated to torch 2.8.0 for better GPU support and performance
FROM pytorch/pytorch:2.8.0-cuda12.6-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# System dependencies for OCR backends and VLM
# Fix GPG signature errors by temporarily ignoring GPG checks to install ca-certificates
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo 'Acquire::AllowInsecureRepositories "true";' > /etc/apt/apt.conf.d/99allow-insecure && \
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99allow-insecure && \
    apt-get update 2>&1 | grep -v "^W:" || true && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    ca-certificates \
    gnupg2 \
    && rm -f /etc/apt/apt.conf.d/99allow-insecure && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    # OpenCV and image processing dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgeos-dev \
    # Tesseract OCR
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    # Additional libs for deep learning
    libopenblas-dev \
    liblapack-dev \
    # ONNX Runtime dependencies
    libprotobuf-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies (PyTorch already installed in base image)
COPY docker/docling-mcp/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code and shared configuration schema
COPY docker/docling-mcp/app /opt/docling-mcp/app
COPY config /opt/docling-mcp/app/config
# AICODE-NOTE: Only copy the src components required by Docling (prompt registry) to avoid shadowing external packages.
COPY src/__init__.py /opt/docling-mcp/app/src/__init__.py
COPY src/prompts /opt/docling-mcp/app/src/prompts
COPY docker/docling-mcp/docker-entrypoint.sh /usr/local/bin/entrypoint.sh

# Create runtime directories
RUN mkdir -p /opt/docling-mcp/models \
    /opt/docling-mcp/logs \
    /opt/docling-mcp/cache && \
    chmod +x /usr/local/bin/entrypoint.sh

# Environment configuration
ENV PYTHONPATH="/opt/docling-mcp/app:${PYTHONPATH}" \
    DOCLING_SETTINGS_PATH=/opt/docling-mcp/config.yaml \
    DOCLING_MODELS_DIR=/opt/docling-mcp/models \
    DOCLING_LOG_DIR=/opt/docling-mcp/logs \
    DOCLING_CACHE_DIR=/opt/docling-mcp/cache \
    HF_HOME=/opt/docling-mcp/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /opt/docling-mcp

VOLUME ["/opt/docling-mcp/models", "/opt/docling-mcp/logs", "/opt/docling-mcp/cache"]

EXPOSE 8077

ENTRYPOINT ["entrypoint.sh"]
CMD ["run"]
