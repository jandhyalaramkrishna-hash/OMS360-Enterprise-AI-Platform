# ============================================================================
# OMS-360 Enterprise Food Delivery System - Version 1.0
# Core Engine Application Dockerfile (Python 3.10-Slim Base)
# ============================================================================

FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging outputs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install system utilities necessary for potential networking diagnostic probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy and install core package dependencies
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Ingest all application module source codes
COPY app/ /workspace/app/
COPY ai/ /workspace/ai/
COPY tests/ /workspace/tests/

EXPOSE 8000

# Set default boot target up to execute our FastAPI app server layer
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]