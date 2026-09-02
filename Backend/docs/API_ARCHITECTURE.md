# API Architecture

Overview of the Agentic Pipeline API architecture and data flow.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                  │
│  (Web App, Mobile App, cURL, Postman, etc.)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP POST /analyze
                         │ {image_url, movie_name, enable_vision}
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER                             │
│                        (api.py)                                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Download Image from URL                              │  │
│  │  2. Create Temporary Input Folder                        │  │
│  │  3. Process through Pipeline                             │  │
│  │  4. Upload Crops to ImgBB                                │  │
│  │  5. Return Results with Hosted URLs                      │  │
│  │  6. Cleanup Temp Files (Background)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────┬───────────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────────┐  ┌────────────────────────────────┐
│  UPDATED AGENTIC PIPELINE  │  │      EXTERNAL SERVICES         │
│ (updated_agentic_pipeline) │  │                                │
│                            │  │  • TMDB API (cast data)        │
│  ┌──────────────────────┐  │  │  • ImgBB API (image hosting)  │
│  │ YOLO Object Detection│  │  │                                │
│  └──────────────────────┘  │  └────────────────────────────────┘
│  ┌──────────────────────┐  │
│  │ InsightFace          │  │
│  │ Face Recognition     │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ TMDB Cast Fetcher    │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ Vision Model         │  │
│  │ (Optional)           │  │
│  └──────────────────────┘  │
└────────────┬───────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL + pgvector                        │
│                                                                 │
│  • face_embeddings table (512-dim vectors)                     │
│  • HNSW index for fast similarity search                       │
│  • Actor metadata (id, name, image_path)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Request Phase

```
Client Request
    ↓
{
  "image_url": "https://example.com/image.jpg",
  "movie_name": "Pathaan",
  "enable_vision": 0,
  "similarity_threshold": 0.6,
  "max_cast": 20
}
    ↓
FastAPI Endpoint (/analyze)
    ↓
Request Validation (Pydantic)
    ↓
Create Unique Request ID
    ↓
Create Temp Directories
```

### 2. Image Download Phase

```
Download Image from URL
    ↓
Save to: temp_api_uploads/{request_id}/input/
    ↓
Validate Image Format
```

### 3. Pipeline Processing Phase

```
Initialize Pipeline
    ↓
┌─────────────────────────────────────┐
│ A. Prepare Movie Cast               │
│    ├─ Search TMDB for movie         │
│    ├─ Fetch cast list (top N)       │
│    ├─ Download actor profile images │
│    ├─ Extract face embeddings       │
│    └─ Store in PostgreSQL           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ B. Detect Objects (YOLO)            │
│    ├─ People                        │
│    ├─ Products                      │
│    ├─ Animals                       │
│    ├─ Vehicles                      │
│    └─ Other objects                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ C. Identify People                  │
│    For each detected person:        │
│    ├─ Crop with padding             │
│    ├─ Extract face embedding        │
│    ├─ Search in database            │
│    │   (only among cast members)    │
│    ├─ Match by similarity           │
│    └─ Save crop to disk             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ D. Vision Analysis (Optional)       │
│    If enable_vision = 1:            │
│    ├─ Analyze scene                 │
│    ├─ Analyze clothing              │
│    ├─ Analyze products              │
│    └─ Analyze other objects         │
└─────────────────────────────────────┘
```

### 4. Image Upload Phase

```
For each cropped image:
    ↓
Upload to ImgBB API
    ↓
Receive hosted URL
    ↓
Replace local path with URL in result
    ↓
Mark as "crop_image_hosted": true
```

### 5. Response Phase

```
Build Response JSON
    ↓
{
  "success": true,
  "message": "Image analyzed successfully",
  "processing_time": 12.34,
  "data": {
    "movie_context": {...},
    "scene_analysis": {...},
    "detections_summary": {...},
    "people": [
      {
        "name": "Shah Rukh Khan",
        "character": "Pathaan",
        "confidence": 87,
        "crop_image": "https://i.ibb.co/xxxxx/person_1.png",
        "crop_image_hosted": true,
        ...
      }
    ],
    "products": [...],
    ...
  }
}
    ↓
Return to Client
    ↓
Schedule Background Cleanup
```

### 6. Cleanup Phase (Background)

```
Background Task
    ↓
Delete temp_api_uploads/{request_id}/
    ↓
Remove all downloaded and cropped images
    ↓
Free disk space
```

## Component Details

### FastAPI Server (`api.py`)

**Responsibilities:**
- HTTP request handling
- Input validation
- Image downloading
- Pipeline orchestration
- Image uploading
- Response formatting
- Background cleanup

**Endpoints:**
- `POST /analyze` - Main analysis endpoint
- `GET /health` - Health check
- `GET /` - API information
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

### Updated Agentic Pipeline (`updated_agentic_pipeline.py`)

**Components:**

1. **TMDBCastFetcher**
   - Searches movies/TV series
   - Fetches cast information
   - Downloads actor profile images
   - Caches images locally

2. **InsightFaceRecognizer**
   - Loads InsightFace model
   - Extracts 512-dim face embeddings
   - Handles face detection failures

3. **FaceEmbeddingDB**
   - PostgreSQL connection
   - pgvector operations
   - Similarity search (cosine distance)
   - Embedding storage

4. **UpdatedAgenticPipeline**
   - Orchestrates all components
   - YOLO object detection
   - Face identification
   - Optional vision analysis
   - Result formatting

### PostgreSQL + pgvector

**Schema:**
```sql
CREATE TABLE face_embeddings (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL,
    actor_name VARCHAR(255) NOT NULL,
    image_path TEXT NOT NULL,
    embedding vector(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(actor_id, image_path)
);

CREATE INDEX face_embeddings_vector_idx 
ON face_embeddings USING hnsw (embedding vector_cosine_ops);
```

**Query Example:**
```sql
-- Find similar faces
SELECT actor_id, actor_name, 
       1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM face_embeddings
WHERE actor_id IN (123, 456, 789)
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### External Services

1. **TMDB API**
   - Movie/TV series search
   - Cast information
   - Actor profile images
   - Rate limit: 40 requests/10 seconds

2. **ImgBB API**
   - Image hosting
   - Returns permanent URLs
   - Free tier: Unlimited uploads
   - Max file size: 32MB

## Performance Characteristics

### Fast Mode (enable_vision=0)

```
Request → Download (1-2s)
       → Prepare Cast (2-5s, cached after first run)
       → Detect Objects (1-2s)
       → Identify People (1-3s)
       → Upload Crops (2-5s)
       → Response
Total: 5-15 seconds
```

### Vision Mode (enable_vision=1)

```
Request → Download (1-2s)
       → Prepare Cast (2-5s, cached)
       → Detect Objects (1-2s)
       → Identify People (1-3s)
       → Vision Analysis (20-40s)
       → Upload Crops (2-5s)
       → Response
Total: 30-60 seconds
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- Shared PostgreSQL database
- Load balancer distribution
- Independent worker processes

### Caching Strategy
1. **Actor Images**: Cached locally in `cache/tmdb/actors/`
2. **Face Embeddings**: Stored in PostgreSQL (persistent)
3. **TMDB Responses**: Could add Redis cache
4. **Analysis Results**: Could cache by image hash

### Database Optimization
- HNSW index for fast vector search
- Actor ID filtering reduces search space
- Connection pooling for concurrent requests
- Regular VACUUM for performance

### Resource Usage
- **CPU**: YOLO detection, face recognition
- **Memory**: Model loading (~2GB), embeddings
- **Disk**: Temporary files, cache (~1GB per 100 actors)
- **Network**: Image downloads, API calls

## Security Considerations

### Input Validation
- URL format validation
- Image size limits
- Parameter range checks
- SQL injection prevention (parameterized queries)

### Rate Limiting
- Per-IP request limits
- API key authentication (optional)
- Timeout protection

### Data Privacy
- Temporary files deleted after processing
- No permanent storage of user images
- Database contains only actor reference images

### Network Security
- HTTPS in production
- CORS configuration
- Firewall rules
- Reverse proxy (Nginx)

## Error Handling

### Client Errors (4xx)
- Invalid image URL
- Unsupported image format
- Invalid parameters
- Missing required fields

### Server Errors (5xx)
- Database connection failure
- External API failures (TMDB, ImgBB)
- Model loading errors
- Processing timeouts

### Graceful Degradation
- Continue without ImgBB if not configured
- Skip vision analysis on model errors
- Return partial results on non-critical failures

## Monitoring & Logging

### Logs
- Request/response logs
- Error logs with stack traces
- Processing time metrics
- External API call logs

### Metrics
- Request count
- Processing time distribution
- Success/failure rates
- Database query performance
- External API latency

### Health Checks
- Database connectivity
- External API availability
- Disk space
- Memory usage

## Future Enhancements

### Performance
- [ ] Redis caching for results
- [ ] Async image processing
- [ ] Batch processing endpoint
- [ ] WebSocket for real-time updates

### Features
- [ ] Multiple image analysis
- [ ] Video frame analysis
- [ ] Custom actor database
- [ ] Face clustering
- [ ] Product search integration

### Infrastructure
- [ ] Kubernetes deployment
- [ ] Auto-scaling
- [ ] CDN integration
- [ ] Multi-region support

## Conclusion

The API provides a production-ready interface to the agentic pipeline with:
- Simple HTTP interface
- Fast processing (5-15s typical)
- Automatic image hosting
- Scalable architecture
- Comprehensive error handling
- Production deployment support
