FROM python:3.11-slim

WORKDIR /app

# System deps for opencv, insightface
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
