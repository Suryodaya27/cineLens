# Updated Agentic Pipeline Setup Guide

## Overview

The updated pipeline provides **fast and accurate actor identification** using:
- **InsightFace** for face recognition (much faster than vision LLMs)
- **TMDB API** for fetching cast data
- **PostgreSQL + pgvector** for efficient similarity search
- **YOLO** for person detection

## Key Improvements

1. ✅ **Supports regional/Indian actors** - Works with any actor in TMDB database
2. ✅ **Much faster** - No slow 8B parameter model inference
3. ✅ **More accurate** - Face embeddings are more reliable than vision model descriptions
4. ✅ **Scalable** - Vector database enables fast search across thousands of actors
5. ✅ **Same I/O format** - Compatible with existing agentic_pipeline.py output

## Prerequisites

### 1. PostgreSQL with pgvector

#### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Install pgvector
brew install pgvector

# Create database
createdb face_recognition
```

#### Ubuntu/Debian
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector
sudo apt install postgresql-15-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb face_recognition
```

#### Docker (easiest option)
```bash
# Run PostgreSQL with pgvector
docker run -d \
  --name pgvector-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=face_recognition \
  -p 5432:5432 \
  ankane/pgvector

# Verify it's running
docker ps
```

### 2. TMDB API Key

1. Sign up at https://www.themoviedb.org/
2. Go to Settings → API → Request API Key
3. Choose "Developer" option
4. Fill in the form (use "Personal" for application type)
5. Copy your API key

Set the environment variable:
```bash
export TMDB_API_KEY=your_api_key_here
```

Or add to `.env` file:
```
TMDB_API_KEY=your_api_key_here
```

### 3. Python Dependencies

```bash
# Install additional dependencies
pip install -r requirements_updated_pipeline.txt

# Or install individually
pip install insightface onnxruntime psycopg2-binary
```

## Configuration

### Database Configuration

The pipeline uses these environment variables (with defaults):

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=face_recognition
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
```

Or add to `.env` file:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

## Usage

### Basic Usage

```bash
python3 updated_agentic_pipeline.py input/image.jpg --movie "Movie Title"
```

### Examples

```bash
# Identify actors in Pathaan
python3 updated_agentic_pipeline.py input/srk_test.jpeg --movie "Pathaan"

# Identify actors in Leo (Tamil movie)
python3 updated_agentic_pipeline.py input/leo_test.webp --movie "Leo"

# Identify actors in Jawan
python3 updated_agentic_pipeline.py input/srk_test2.jpeg --movie "Jawan"

# Specify output directory
python3 updated_agentic_pipeline.py input/rdj.jpg --movie "Iron Man" -o my-output

# Adjust similarity threshold (higher = stricter matching)
python3 updated_agentic_pipeline.py input/image.jpg --movie "Avengers" --threshold 0.7

# Process more cast members
python3 updated_agentic_pipeline.py input/image.jpg --movie "Movie" --max-cast 30
```

### Command Line Options

```
positional arguments:
  image                 Input image file

required arguments:
  --movie TITLE         Movie or series title

optional arguments:
  -o, --output DIR      Output directory (default: final-output)
  --yolo-model MODEL    YOLO model (default: yolov8n.pt)
  --threshold FLOAT     Face similarity threshold 0-1 (default: 0.6)
  --max-cast INT        Maximum cast members to process (default: 20)
  --images-per-actor N  Profile images per actor (default: 5)
```

## How It Works

### Pipeline Flow

1. **Fetch Cast Data**
   - Search TMDB for movie/series title
   - Retrieve cast list (top 20 by default)
   - Download profile images for each actor

2. **Generate Face Embeddings**
   - Use InsightFace to extract 512-dimensional face embeddings
   - Store embeddings in PostgreSQL with pgvector
   - Cache images locally to avoid re-downloading

3. **Detect People in Image**
   - Use YOLO to detect all people in the input image
   - Crop each detected person with padding

4. **Identify Actors**
   - Extract face embedding from each cropped person
   - Search for similar embeddings in database (only among cast members)
   - Match if similarity score exceeds threshold

5. **Generate Output**
   - Create JSON output matching agentic_pipeline.py format
   - Save cropped images
   - Print summary

### Similarity Threshold

The `--threshold` parameter controls matching strictness:

- **0.4-0.5**: Very lenient (may have false positives)
- **0.6**: Balanced (default, recommended)
- **0.7-0.8**: Strict (fewer false positives, may miss some matches)
- **0.9+**: Very strict (only very clear matches)

## Output Format

The output JSON matches `agentic_pipeline.py` format:

```json
{
  "source_image": "image.jpg",
  "movie_context": {
    "title": "Movie Title",
    "year": "2023",
    "cast": ["Actor 1", "Actor 2", ...]
  },
  "scene_analysis": {
    "setting": "Not analyzed (fast mode)",
    ...
  },
  "detections_summary": {
    "people": 2
  },
  "people": [
    {
      "name": "Shah Rukh Khan",
      "profession": "Actor",
      "character": "Pathaan",
      "confidence": 87,
      "similarity_score": 0.87,
      "crop_image": "final-output/image_person_1.png",
      "detection_confidence": 0.95,
      ...
    }
  ],
  "products": [],
  "animals": [],
  ...
}
```

## Performance Comparison

| Feature | Old Pipeline (Qwen 8B) | Updated Pipeline (InsightFace) |
|---------|------------------------|--------------------------------|
| Speed per person | ~30-60 seconds | ~1-2 seconds |
| Accuracy | Moderate | High |
| Regional actors | Limited | Full TMDB support |
| Scalability | Poor | Excellent |
| Offline capable | Yes | No (needs TMDB API) |

## Troubleshooting

### Database Connection Error

```
❌ Database connection failed: could not connect to server
```

**Solution**: Make sure PostgreSQL is running
```bash
# macOS
brew services start postgresql@15

# Linux
sudo systemctl start postgresql

# Docker
docker start pgvector-db
```

### pgvector Extension Not Found

```
❌ ERROR: extension "vector" is not available
```

**Solution**: Install pgvector extension
```bash
# macOS
brew install pgvector

# Ubuntu
sudo apt install postgresql-15-pgvector

# Or use Docker image with pgvector pre-installed
docker run -d --name pgvector-db -p 5432:5432 ankane/pgvector
```

### TMDB API Key Error

```
❌ TMDB API key required
```

**Solution**: Set your API key
```bash
export TMDB_API_KEY=your_key_here
```

### InsightFace Installation Issues

```
❌ ImportError: No module named 'insightface'
```

**Solution**: Install InsightFace
```bash
pip install insightface onnxruntime
```

### No Faces Detected

```
⚠️ No faces detected in images
```

**Possible causes**:
- Actor profile images don't show clear faces
- Images are too low quality
- Try increasing `--images-per-actor` to download more images

### Low Confidence Matches

**Solution**: Adjust threshold
```bash
# Lower threshold for more lenient matching
python3 updated_agentic_pipeline.py image.jpg --movie "Title" --threshold 0.5

# Or increase images per actor for better embeddings
python3 updated_agentic_pipeline.py image.jpg --movie "Title" --images-per-actor 10
```

## Caching

The pipeline caches data to improve performance:

- **Actor images**: `cache/tmdb/actor_<id>/`
- **Face embeddings**: PostgreSQL database

To clear cache:
```bash
# Clear image cache
rm -rf cache/tmdb/

# Clear database embeddings
psql face_recognition -c "TRUNCATE face_embeddings;"
```

## Advanced Usage

### Using with Multiple Movies

The database accumulates embeddings across runs, so subsequent runs are faster:

```bash
# First run - downloads and processes cast
python3 updated_agentic_pipeline.py img1.jpg --movie "Pathaan"

# Second run - reuses cached data if same actors
python3 updated_agentic_pipeline.py img2.jpg --movie "Jawan"
```

### Batch Processing

```bash
# Process multiple images from same movie
for img in input/*.jpg; do
  python3 updated_agentic_pipeline.py "$img" --movie "Leo"
done
```

### Custom Database

```bash
# Use remote database
export POSTGRES_HOST=db.example.com
export POSTGRES_PORT=5432
export POSTGRES_USER=myuser
export POSTGRES_PASSWORD=mypassword

python3 updated_agentic_pipeline.py image.jpg --movie "Title"
```

## Limitations

1. **Requires internet** - Needs TMDB API access
2. **TMDB coverage** - Only works for movies/actors in TMDB database
3. **Face visibility** - Requires clear face visibility in both profile images and input image
4. **Scene analysis** - Skips detailed scene analysis for speed (use original pipeline if needed)

## Future Enhancements

Possible improvements:
- [ ] Add GPU acceleration for InsightFace
- [ ] Support for custom actor databases
- [ ] Hybrid mode: face recognition + vision LLM for unknown people
- [ ] Multi-face tracking across video frames
- [ ] Age-invariant face matching
- [ ] Pose-invariant face matching

## Support

For issues or questions:
1. Check troubleshooting section above
2. Verify all prerequisites are installed
3. Check database connection and TMDB API key
4. Review error messages carefully
