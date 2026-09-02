# API Quick Start Guide

Get the Agentic Pipeline API running in 5 minutes!

## Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension
- TMDB API key (free)
- ImgBB API key (free)

## Step 1: Install Dependencies

```bash
pip install -r requirements_api.txt
```

## Step 2: Configure Environment

Create or update `.env` file:

```bash
# Required
TMDB_API_KEY=your_tmdb_api_key
IMGBB_API_KEY=your_imgbb_api_key

# PostgreSQL (defaults shown)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

**Get API Keys:**
- TMDB: https://www.themoviedb.org/settings/api
- ImgBB: https://api.imgbb.com/

## Step 3: Start PostgreSQL

Using Docker (recommended):
```bash
docker-compose up -d
```

Or install locally - see `docs/UPDATED_PIPELINE_SETUP.md`

## Step 4: Start API Server

Option A - Using the start script:
```bash
./start_api.sh
```

Option B - Direct command:
```bash
python api.py
```

Option C - Using uvicorn:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## Step 5: Test the API

### Using the test script:
```bash
python test_api.py
```

### Using curl:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://i.ibb.co/9ZQZ8Zq/srk-test.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 0
  }'
```

### Using the example client:
```bash
python api_client_example.py
```

### Using Postman:
1. Import `Agentic_Pipeline_API.postman_collection.json`
2. Set `base_url` variable to `http://localhost:8000`
3. Run any request

## API Endpoints

### POST /analyze
Analyze an image with movie context.

**Request:**
```json
{
  "image_url": "https://example.com/image.jpg",
  "movie_name": "Pathaan",
  "enable_vision": 0,
  "similarity_threshold": 0.6,
  "max_cast": 20
}
```

**Response:**
```json
{
  "success": true,
  "message": "Image analyzed successfully",
  "processing_time": 12.34,
  "data": {
    "movie_context": {...},
    "scene_analysis": {...},
    "people": [...],
    "products": [...],
    ...
  }
}
```

### GET /health
Check API health and configuration.

### GET /
API information and documentation links.

## Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Common Issues

### "Failed to download image"
- Check if the image URL is accessible
- Ensure URL points directly to an image file

### "TMDB API key required"
- Set `TMDB_API_KEY` in `.env` file
- Get free key at https://www.themoviedb.org/settings/api

### "Database connection failed"
- Ensure PostgreSQL is running: `docker-compose up -d`
- Check credentials in `.env` file

### "No ImgBB API key"
- Set `IMGBB_API_KEY` in `.env` file
- API works without it but won't upload cropped images

## Next Steps

1. Read full documentation: `API_README.md`
2. Check example client: `api_client_example.py`
3. Import Postman collection for easy testing
4. Review pipeline documentation: `docs/UPDATED_PIPELINE_README.md`

## Support

For detailed setup and troubleshooting:
- API Documentation: `API_README.md`
- Pipeline Setup: `docs/UPDATED_PIPELINE_SETUP.md`
- Pipeline Guide: `docs/UPDATED_PIPELINE_README.md`
