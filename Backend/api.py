#!/usr/bin/env python3
"""
FastAPI wrapper for the Updated Agentic Pipeline.

Accepts image URLs and movie names, processes them through the pipeline,
uploads cropped images to ImgBB, and returns results with hosted URLs.

Usage:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

API Endpoints:
    POST /analyze - Analyze image with movie context
    GET /health - Health check
"""

import os
import json
import tempfile
import shutil
import requests
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl, Field
import uvicorn

from pipelines.updated_agentic_pipeline import UpdatedAgenticPipeline
from services.tmdb_enrichment import TMDBEnricher
from services.unified_shopping import UnifiedShopper
from logging_config import get_logger

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = get_logger("api")

# Configuration
IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')
if not IMGBB_API_KEY:
    logger.warning("IMGBB_API_KEY not set — image uploads will fail")

# Vision model configuration
DEFAULT_VISION_MODEL = os.getenv('VISION_MODEL', 'qwen3.8:latest')

TEMP_DIR = Path("temp_api_uploads")
TEMP_DIR.mkdir(exist_ok=True)


# FastAPI app
app = FastAPI(
    title="Agentic Pipeline API",
    description="AI-powered image analysis with actor identification and object detection",
    version="1.0.0"
)


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request model for image analysis."""
    image_url: HttpUrl = Field(..., description="URL of the image to analyze")
    movie_name: str = Field(..., description="Name of the movie or TV series")
    enable_vision: int = Field(default=0, description="Enable vision analysis (0=disabled, 1=enabled)")
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Face similarity threshold (0-1)")
    max_cast: int = Field(default=20, ge=1, le=50, description="Maximum cast members to process")
    vision_model: Optional[str] = Field(default=None, description="Vision model name (e.g., 'llama3.2-vision:11b', 'qwen3-vl:8b')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/image.jpg",
                "movie_name": "Pathaan",
                "enable_vision": 0,
                "similarity_threshold": 0.6,
                "max_cast": 20,
                "vision_model": "llama3.2-vision:11b"
            }
        }


class AnalyzeResponse(BaseModel):
    """Response model for image analysis."""
    success: bool
    message: str
    data: Optional[Dict] = None
    processing_time: Optional[float] = None


class ActorMoviesRequest(BaseModel):
    """Request model for actor movies endpoint."""
    actor_name: str = Field(..., description="Name of the actor")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of movies to return")
    sort_by: str = Field(default="recent", description="Sort by 'recent' or 'rating'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "actor_name": "Shah Rukh Khan",
                "limit": 10,
                "sort_by": "recent"
            }
        }


class ActorMoviesResponse(BaseModel):
    """Response model for actor movies."""
    success: bool
    message: str
    data: Optional[Dict] = None


class ShoppingRequest(BaseModel):
    """Request model for shopping recommendations."""
    analysis_data: Dict = Field(..., description="Analysis JSON data from /analyze endpoint")
    max_products_per_item: int = Field(default=5, ge=1, le=20, description="Max products per text search")
    max_visual_results: int = Field(default=10, ge=1, le=30, description="Max results per visual search")
    amazon_region: str = Field(default="com", description="Amazon region (com, in, co.uk, etc.)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_data": {
                    "people": [
                        {
                            "name": "Shah Rukh Khan",
                            "clothing": {
                                "description": "Black leather jacket",
                                "colors": ["black"],
                                "style": "casual"
                            }
                        }
                    ],
                    "products": []
                },
                "max_products_per_item": 5,
                "max_visual_results": 10,
                "amazon_region": "com"
            }
        }


class ShoppingResponse(BaseModel):
    """Response model for shopping recommendations."""
    success: bool
    message: str
    data: Optional[Dict] = None


# Helper functions
class ImgBBUploader:
    """Upload images to ImgBB hosting service."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.upload_url = "https://api.imgbb.com/1/upload"
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload image and return hosted URL."""
        if not self.api_key:
            logger.warning("Cannot upload, no ImgBB API key", extra={"detail": Path(image_path).name})
            return None
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {'key': self.api_key}
                
                response = requests.post(self.upload_url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if result.get('success'):
                    url = result['data']['url']
                    logger.debug("Uploaded to ImgBB", extra={"detail": f"{Path(image_path).name} -> {url}"})
                    return url
                else:
                    logger.error("ImgBB upload failed", extra={"error": result.get('error', {}).get('message', 'Unknown')})
                    return None
        
        except Exception as e:
            logger.error("ImgBB upload error", extra={"error": str(e), "detail": Path(image_path).name})
            return None


def download_image(url: str, save_path: Path) -> bool:
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info("Image downloaded", extra={"detail": save_path.name})
        return True
    
    except Exception as e:
        logger.error("Image download failed", extra={"error": str(e)})
        return False


def upload_cropped_images(result: Dict, uploader: ImgBBUploader) -> Dict:
    """Upload all cropped images to ImgBB and replace local paths with URLs."""
    
    # Upload person crops
    for person in result.get('people', []):
        if 'crop_image' in person and person['crop_image']:
            crop_path = person['crop_image']
            if os.path.exists(crop_path):
                hosted_url = uploader.upload_image(crop_path)
                if hosted_url:
                    person['crop_image'] = hosted_url
                    person['crop_image_hosted'] = True
                else:
                    person['crop_image_hosted'] = False
    
    # Upload other object crops
    for category in ['products', 'animals', 'vehicles', 'electronics', 'furniture', 'other_objects']:
        for obj in result.get(category, []):
            if 'crop_image' in obj and obj['crop_image']:
                crop_path = obj['crop_image']
                if os.path.exists(crop_path):
                    hosted_url = uploader.upload_image(crop_path)
                    if hosted_url:
                        obj['crop_image'] = hosted_url
                        obj['crop_image_hosted'] = True
                    else:
                        obj['crop_image_hosted'] = False
    
    return result


def cleanup_temp_files(temp_dir: Path):
    """Clean up temporary files after processing."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug("Cleaned up temp dir", extra={"detail": str(temp_dir)})
    except Exception as e:
        logger.warning("Cleanup warning", extra={"error": str(e)})


# API endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agentic Pipeline API",
        "version": "1.0.0",
        "description": "AI-powered image analysis with actor identification",
        "endpoints": {
            "POST /analyze": "Analyze image with movie context",
            "POST /api/more-movies": "Get actor's movies from TMDB",
            "POST /api/shopping-recommendations": "Get shopping recommendations from analysis",
            "GET /health": "Health check"
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "imgbb_configured": bool(IMGBB_API_KEY),
        "tmdb_configured": bool(os.getenv('TMDB_API_KEY'))
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze image with movie context.
    
    This endpoint:
    1. Downloads the image from the provided URL
    2. Creates a temporary input folder
    3. Processes the image through the agentic pipeline
    4. Uploads all cropped images to ImgBB
    5. Returns results with hosted image URLs
    6. Cleans up temporary files in the background
    """
    start_time = datetime.now()
    
    # Create unique temp directory for this request
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_request_dir = TEMP_DIR / request_id
    temp_input_dir = temp_request_dir / "input"
    temp_output_dir = temp_request_dir / "output"
    
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("Analyze request", extra={"request_id": request_id, "image_url": str(request.image_url), "movie": request.movie_name})
        
        # Download image
        image_filename = f"input_image_{request_id}.jpg"
        image_path = temp_input_dir / image_filename
        
        if not download_image(str(request.image_url), image_path):
            raise HTTPException(
                status_code=400,
                detail="Failed to download image from provided URL"
            )
        
        # Initialize pipeline
        logger.info("Initializing pipeline", extra={"request_id": request_id})
        vision_model = request.vision_model or DEFAULT_VISION_MODEL
        
        pipeline = UpdatedAgenticPipeline(
            yolo_model="yolov8n.pt",
            vision_model=vision_model,
            use_vision_analysis=bool(request.enable_vision)
        )
        
        # Process image
        logger.info("Processing image", extra={"request_id": request_id})
        result = pipeline.process_image(
            image_path=str(image_path),
            movie_title=request.movie_name,
            output_dir=str(temp_output_dir),
            similarity_threshold=request.similarity_threshold
        )
        
        pipeline.close()
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Pipeline processing failed"
            )
        
        # Upload cropped images to ImgBB
        logger.info("Uploading crops", extra={"request_id": request_id})
        if IMGBB_API_KEY:
            uploader = ImgBBUploader(IMGBB_API_KEY)
            result = upload_cropped_images(result, uploader)
        else:
            logger.warning("Skipping uploads — no ImgBB API key", extra={"request_id": request_id})
            result['warning'] = "Cropped images not uploaded: ImgBB API key not configured"
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Schedule cleanup in background
        background_tasks.add_task(cleanup_temp_files, temp_request_dir)
        
        logger.info("Request completed", extra={"request_id": request_id, "duration": f"{processing_time:.2f}s"})
        
        return AnalyzeResponse(
            success=True,
            message="Image analyzed successfully",
            data=result,
            processing_time=processing_time
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        cleanup_temp_files(temp_request_dir)
        raise
    
    except Exception as e:
        # Clean up on error
        cleanup_temp_files(temp_request_dir)
        
        logger.exception("Request failed", extra={"request_id": request_id, "error": str(e)})
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Redis job queue + SSE streaming
# ---------------------------------------------------------------------------

import asyncio
import hashlib
import redis as _redis

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
JOB_QUEUE = 'cinelens:jobs'
CACHE_TTL = 86400  # cached results expire after 24 hours

def _get_redis():
    return _redis.Redis.from_url(REDIS_URL, decode_responses=True)

def _cache_key(image_url: str, movie_name: str) -> str:
    """Deterministic cache key from image URL + movie name."""
    raw = f"{movie_name.strip().lower()}:{image_url.strip()}"
    return f"cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

def _sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/analyze-stream")
async def analyze_image_stream(request: AnalyzeRequest):
    """Enqueue job to Redis worker and stream progress via SSE. Returns cached result if available."""

    r = _get_redis()
    cache_k = _cache_key(str(request.image_url), request.movie_name)

    # Check cache first
    cached = r.get(cache_k)
    if cached:
        async def from_cache():
            result = json.loads(cached)
            yield _sse("progress", {"step": "download", "message": "Cache hit", "done": True})
            yield _sse("complete", result)
        return StreamingResponse(from_cache(), media_type="text/event-stream")

    # No cache — enqueue job
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    job_payload = {
        "job_id": job_id,
        "cache_key": cache_k,
        "params": {
            "image_url": str(request.image_url),
            "movie_name": request.movie_name,
            "enable_vision": request.enable_vision,
            "similarity_threshold": request.similarity_threshold,
            "max_cast": request.max_cast,
            "vision_model": request.vision_model,
        }
    }
    r.rpush(JOB_QUEUE, json.dumps(job_payload))
    r.hset(f"job:{job_id}", "status", "queued")

    async def generate():
        """Subscribe to the job's pub/sub channel and forward events as SSE."""
        sub = _get_redis()  # separate connection for blocking subscribe
        pubsub = sub.pubsub()
        pubsub.subscribe(f"job:{job_id}")

        try:
            # First, replay any events we may have missed (worker started fast)
            existing = sub.lrange(f"job:{job_id}:events", 0, -1)
            for raw in existing:
                msg = json.loads(raw)
                yield _sse(msg["event"], msg["data"])
                if msg["event"] in ("complete", "error"):
                    return

            # Now listen for new events
            seen = len(existing)
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    msg = json.loads(message['data'])
                    yield _sse(msg["event"], msg["data"])
                    if msg["event"] in ("complete", "error"):
                        return
                else:
                    # Check if job finished while we were waiting
                    status = sub.hget(f"job:{job_id}", "status")
                    if status in ("complete", "error"):
                        # Drain any remaining events
                        remaining = sub.lrange(f"job:{job_id}:events", seen, -1)
                        for raw in remaining:
                            msg = json.loads(raw)
                            yield _sse(msg["event"], msg["data"])
                        return

                await asyncio.sleep(0)  # yield control

        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/jobs/{job_id}")
async def get_job_result(job_id: str):
    """Retrieve a stored job result from Redis."""
    r = _get_redis()
    status = r.hget(f"job:{job_id}", "status")
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    if status == "processing" or status == "queued":
        return JSONResponse({"status": status, "data": None})
    if status == "error":
        return JSONResponse({"status": "error", "data": None})
    raw = r.hget(f"job:{job_id}", "result")
    if not raw:
        raise HTTPException(status_code=404, detail="Result expired")
    return JSONResponse({"status": "complete", **json.loads(raw)})
async def get_actor_movies(request: ActorMoviesRequest):
    """
    Get actor's movies from TMDB.
    
    This endpoint:
    1. Searches for the actor on TMDB
    2. Fetches their filmography
    3. Returns movies sorted by recent or rating
    4. Includes poster images and details
    """
    try:
        logger.info("Actor movies request", extra={"actor": request.actor_name, "detail": f"limit={request.limit} sort={request.sort_by}"})
        
        # Initialize TMDB enricher
        enricher = TMDBEnricher()
        
        # Search for actor
        search_result = enricher.search_person(request.actor_name)
        
        if not search_result:
            raise HTTPException(
                status_code=404,
                detail=f"Actor not found: {request.actor_name}"
            )
        
        person_id = search_result['id']
        logger.info("Actor found", extra={"actor": search_result['name'], "detail": f"TMDB ID {person_id}"})
        
        # Get person details
        details = enricher.get_person_details(person_id)
        
        # Get credits
        credits_data = enricher.get_person_credits(person_id, limit=50)  # Get more to sort
        
        # Sort movies
        movies = credits_data['recent_credits']
        
        if request.sort_by == "rating":
            movies = sorted(
                movies,
                key=lambda x: x.get('vote_average', 0),
                reverse=True
            )
        
        # Limit results
        movies = movies[:request.limit]
        
        # Build response
        actor_data = {
            'tmdb_id': person_id,
            'name': search_result['name'],
            'known_for_department': search_result.get('known_for_department'),
            'popularity': search_result.get('popularity'),
            'profile_image': f"{enricher.image_base_url}{search_result['profile_path']}" if search_result.get('profile_path') else None,
            'biography': details.get('biography') if details else None,
            'birthday': details.get('birthday') if details else None,
            'place_of_birth': details.get('place_of_birth') if details else None,
            'total_credits': credits_data['total_credits'],
            'movies': movies
        }
        
        logger.info("Actor movies response", extra={"actor": search_result['name'], "count": len(movies)})
        
        return ActorMoviesResponse(
            success=True,
            message=f"Found {len(movies)} movies for {search_result['name']}",
            data=actor_data
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception("Actor movies failed", extra={"error": str(e)})
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/api/shopping-recommendations", response_model=ShoppingResponse)
async def get_shopping_recommendations(request: ShoppingRequest, background_tasks: BackgroundTasks):
    """
    Get shopping recommendations based on analysis data.
    
    This endpoint:
    1. Accepts analysis JSON from /analyze endpoint
    2. Extracts clothing, products, electronics, furniture
    3. Performs text search (Amazon) for clothing
    4. Performs visual search (SerpAPI) for products
    5. Returns shopping recommendations with product links
    """
    # Create unique temp directory for this request
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_request_dir = TEMP_DIR / f"shopping_{request_id}"
    temp_request_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle both formats: direct analysis data or full API response
    raw_data = request.analysis_data

    if 'success' in raw_data and 'analysis_data' in raw_data:
        analysis_data = raw_data['analysis_data']
    else:
        analysis_data = raw_data

    logger.info("Shopping request", extra={
        "request_id": request_id,
        "detail": f"region={request.amazon_region} people={len(analysis_data.get('people', []))} products={len(analysis_data.get('products', []))}"
    })
    logger.debug("Shopping input data keys: %s", list(analysis_data.keys()))

    try:
        # Save analysis data to temp file
        analysis_file = temp_request_dir / "analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        # Initialize unified shopper
        shopper = UnifiedShopper(
            amazon_region=request.amazon_region,
            visual_provider="serpapi"
        )
        
        # Get shopping recommendations
        logger.info("Finding shopping recommendations", extra={"request_id": request_id})
        output_file = temp_request_dir / "shopping_results.json"
        
        enriched_analysis = shopper.enrich_with_unified_shopping(
            str(analysis_file),
            str(output_file),
            max_products_per_item=request.max_products_per_item,
            max_visual_results=request.max_visual_results
        )
        
        # Extract shopping results
        shopping_results = enriched_analysis.get('unified_shopping_results', [])
        metadata = enriched_analysis.get('unified_shopping_metadata', {})
        
        # Build response
        response_data = {
            'shopping_results': shopping_results,
            'metadata': metadata,
            'summary': {
                'total_searches': metadata.get('total_searches', 0),
                'text_searches': metadata.get('text_searches', 0),
                'visual_searches': metadata.get('visual_searches', 0),
                'total_products_found': metadata.get('total_products_found', 0)
            }
        }
        
        # Schedule cleanup in background
        background_tasks.add_task(cleanup_temp_files, temp_request_dir)
        
        logger.info("Shopping complete", extra={
            "request_id": request_id,
            "count": metadata.get('total_products_found', 0),
            "detail": f"{metadata.get('total_searches', 0)} searches"
        })
        
        return ShoppingResponse(
            success=True,
            message=f"Found {metadata.get('total_products_found', 0)} products across {metadata.get('total_searches', 0)} searches",
            data=response_data
        )
    
    except Exception as e:
        # Clean up on error
        cleanup_temp_files(temp_request_dir)
        
        logger.exception("Shopping request failed", extra={"request_id": request_id, "error": str(e)})
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Run server
if __name__ == "__main__":
    logger.info("Starting API server", extra={"port": 8000})
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
