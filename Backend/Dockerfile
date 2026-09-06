FROM python:3.11-slim

WORKDIR /app

# System deps for opencv, insightface
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Point InsightFace model cache to /ml_cache (mount as volume to persist across rebuilds)
RUN mkdir -p /ml_cache/insightface \
    && ln -s /ml_cache/insightface /root/.insightface

# Default: run the API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
