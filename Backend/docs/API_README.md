# Agentic Pipeline API

FastAPI-based REST API for the Updated Agentic Pipeline. Accepts image URLs and movie names, processes them through the AI pipeline, and returns results with hosted image URLs.

## Features

- 🌐 **REST API**: Simple HTTP endpoints for image analysis
- 📥 **URL-based Input**: Accepts image URLs (no file uploads needed)
- 🎬 **Movie Context**: Identifies actors from specific movies/TV series
- 🖼️ **Image Hosting**: Automatically uploads cropped images to ImgBB
- ⚡ **Fast Processing**: Uses InsightFace for quick face recognition
- 🔍 **Object Detection**: Detects people, products, animals, vehicles, etc.
- 👁️ **Optional Vision Analysis**: Deep analysis with vision models (slower but detailed)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_api.txt
```

### 2. Configure Environment Variables

Create or update `.env` file:

```bash
# Required
TMDB_API_KEY=your_tmdb_api_key_here
IMGBB_API_KEY=your_imgbb_api_key_here

# PostgreSQL (use defaults or customize)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

**Get API Keys:**
- TMDB: https://www.themoviedb.org/settings/api (free)
- ImgBB: https://api.imgbb.com/ (free)

### 3. Start PostgreSQL with pgvector

```bash
# Using Docker
docker-compose up -d

# Or install locally (see docs/UPDATED_PIPELINE_SETUP.md)
```

### 4. Run the API Server

```bash
python api.py
```

Or with uvicorn:

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: http://localhost:8000

## API Endpoints

### POST /analyze

Analyze an image with movie context.

### POST /api/more-movies

Get actor's movies from TMDB.

**Request Body:**

```json
{
  "image_url": "https://example.com/image.jpg",
  "movie_name": "Pathaan",
  "enable_vision": 0,
  "similarity_threshold": 0.6,
  "max_cast": 20,
  "vision_model": "llama3.2-vision:11b"
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image_url` | string (URL) | ✓ | - | URL of the image to analyze |
| `movie_name` | string | ✓ | - | Name of the movie or TV series |
| `enable_vision` | integer | | 0 | Enable vision analysis (0=disabled, 1=enabled) |
| `similarity_threshold` | float | | 0.6 | Face similarity threshold (0.0-1.0) |
| `max_cast` | integer | | 20 | Maximum cast members to process (1-50) |
| `vision_model` | string | | llama3.2-vision:11b | Vision model name (e.g., 'qwen3-vl:8b', 'llava:13b') |

**Response:**

```json
{
  "success": true,
  "message": "Image analyzed successfully",
  "processing_time": 12.34,
  "data": {
    "source_image": "input_image.jpg",
    "movie_context": {
      "title": "Pathaan",
      "year": "2023",
      "cast": ["Shah Rukh Khan", "Deepika Padukone", "John Abraham"]
    },
    "scene_analysis": {
      "setting": "Indoor office",
      "lighting": "Natural daylight",
      "mood": "Professional"
    },
    "detections_summary": {
      "people": 2,
      "products": 1,
      "animals": 0,
      "vehicles": 0
    },
    "people": [
      {
        "name": "Shah Rukh Khan",
        "character": "Pathaan",
        "confidence": 87,
        "similarity_score": 0.87,
        "crop_image": "https://i.ibb.co/xxxxx/person_1.png",
        "crop_image_hosted": true,
        "gender": "male",
        "clothing": {
          "description": "Black leather jacket",
          "colors": ["black"],
          "style": "casual"
        }
      }
    ],
    "products": [],
    "animals": [],
    "vehicles": []
  }
}
```

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "imgbb_configured": true,
  "tmdb_configured": true
}
```

### GET /

API information and available endpoints.

---

## Actor Movies Endpoint

### POST /api/more-movies

Get an actor's filmography from TMDB.

**Request Body:**

```json
{
  "actor_name": "Shah Rukh Khan",
  "limit": 10,
  "sort_by": "recent"
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `actor_name` | string | ✓ | - | Name of the actor |
| `limit` | integer | | 10 | Maximum number of movies to return (1-50) |
| `sort_by` | string | | recent | Sort by 'recent' or 'rating' |

**Response:**

```json
{
  "success": true,
  "message": "Found 10 movies for Shah Rukh Khan",
  "data": {
    "tmdb_id": 41091,
    "name": "Shah Rukh Khan",
    "known_for_department": "Acting",
    "popularity": 45.678,
    "profile_image": "https://image.tmdb.org/t/p/w500/abc123.jpg",
    "biography": "Shah Rukh Khan, also known as SRK...",
    "birthday": "1965-11-02",
    "place_of_birth": "New Delhi, India",
    "total_credits": 95,
    "movies": [
      {
        "title": "Pathaan",
        "type": "movie",
        "release_date": "2023-01-25",
        "character": "Pathaan",
        "vote_average": 7.2,
        "poster_path": "https://image.tmdb.org/t/p/w500/xyz789.jpg",
        "tmdb_id": 840326
      }
    ]
  }
}
```

---

## Usage Examples

### cURL

```bash
# Basic analysis (fast mode)
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/movie-scene.jpg",
    "movie_name": "Pathaan"
  }'

# Get actor movies (recent)
curl -X POST "http://localhost:8000/api/more-movies" \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "Shah Rukh Khan",
    "limit": 10,
    "sort_by": "recent"
  }'

# Get actor movies (top rated)
curl -X POST "http://localhost:8000/api/more-movies" \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "Shah Rukh Khan",
    "limit": 10,
    "sort_by": "rating"
  }'

# With vision analysis (detailed but slower)
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/movie-scene.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 1,
    "similarity_threshold": 0.7,
    "vision_model": "qwen3-vl:8b"
  }'
```

### Python

```python
import requests

# Analyze image
response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "image_url": "https://example.com/movie-scene.jpg",
        "movie_name": "Pathaan",
        "enable_vision": 0,
        "similarity_threshold": 0.6
    }
)

result = response.json()

if result["success"]:
    print(f"Processing time: {result['processing_time']:.2f}s")
    
    # Print identified people
    for person in result["data"]["people"]:
        if person["name"]:
            print(f"✓ {person['name']} ({person['confidence']}%)")
            print(f"  Crop: {person['crop_image']}")
else:
    print(f"Error: {result['message']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function analyzeImage() {
  try {
    const response = await axios.post('http://localhost:8000/analyze', {
      image_url: 'https://example.com/movie-scene.jpg',
      movie_name: 'Pathaan',
      enable_vision: 0,
      similarity_threshold: 0.6
    });
    
    const result = response.data;
    
    if (result.success) {
      console.log(`Processing time: ${result.processing_time}s`);
      
      // Print identified people
      result.data.people.forEach(person => {
        if (person.name) {
          console.log(`✓ ${person.name} (${person.confidence}%)`);
          console.log(`  Crop: ${person.crop_image}`);
        }
      });
    }
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

analyzeImage();
```

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## How It Works

1. **Download Image**: API downloads the image from the provided URL
2. **Create Input Folder**: Temporary folder created for this request
3. **Process Pipeline**: Image processed through the agentic pipeline
   - Detect objects with YOLO
   - Identify actors using InsightFace + pgvector
   - Optional: Analyze scene/clothing with vision models
4. **Upload Crops**: All cropped images uploaded to ImgBB
5. **Return Results**: JSON response with hosted image URLs
6. **Cleanup**: Temporary files deleted in background

## Configuration

### Vision Analysis

Vision analysis provides detailed information about:
- Scene setting, lighting, mood
- Person clothing, pose, expression
- Product brands, materials, features
- Animal breeds, activities
- Vehicle makes, models

**Trade-offs:**
- `enable_vision: 0` (default): Fast, actor identification only (~5-10s)
- `enable_vision: 1`: Detailed analysis, slower (~30-60s depending on objects)

### Similarity Threshold

Controls face matching sensitivity:
- `0.5`: Very lenient (more false positives)
- `0.6`: Balanced (default, recommended)
- `0.7`: Strict (fewer false positives, may miss some matches)
- `0.8`: Very strict (high confidence only)

### Max Cast

Limits the number of cast members to process:
- Lower values (10-15): Faster processing, main cast only
- Higher values (20-30): More comprehensive, includes supporting actors
- Maximum: 50

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid URL, parameters)
- `500`: Internal server error (processing failed)

**Example Error Response:**

```json
{
  "success": false,
  "message": "Failed to download image from provided URL",
  "data": null,
  "processing_time": null
}
```

## Performance

Typical processing times (on modern CPU):

| Mode | Objects | Time |
|------|---------|------|
| Fast (no vision) | 1-2 people | 5-10s |
| Fast (no vision) | 3-5 people | 10-15s |
| Vision enabled | 1-2 people | 30-45s |
| Vision enabled | 5+ objects | 60-90s |

**Optimization Tips:**
1. Use fast mode (`enable_vision: 0`) for actor identification only
2. Lower `max_cast` if you only need main actors
3. Use appropriate `similarity_threshold` to avoid unnecessary processing
4. Consider caching results for frequently analyzed images

## Deployment

### Production Deployment

For production, use a production-grade ASGI server:

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

For production, set these environment variables:

```bash
TMDB_API_KEY=your_key
IMGBB_API_KEY=your_key
POSTGRES_HOST=your_db_host
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

## Troubleshooting

### "Failed to download image"
- Check if the image URL is accessible
- Ensure the URL points directly to an image file
- Try accessing the URL in a browser

### "TMDB API key required"
- Set `TMDB_API_KEY` in `.env` file
- Get a free key at https://www.themoviedb.org/settings/api

### "Database connection failed"
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify pgvector extension is installed

### "No ImgBB API key"
- Set `IMGBB_API_KEY` in `.env` file
- Get a free key at https://api.imgbb.com/
- API will still work but won't upload cropped images

### "No faces detected"
- Image may not contain clear faces
- Try adjusting image quality or angle
- Lower `similarity_threshold` for more lenient matching

## Support

For issues and questions:
1. Check the main documentation in `docs/`
2. Review `UPDATED_PIPELINE_README.md` for pipeline details
3. Check `UPDATED_PIPELINE_SETUP.md` for setup instructions

## License

Same as the main project.
