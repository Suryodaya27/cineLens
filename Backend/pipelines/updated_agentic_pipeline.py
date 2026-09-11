#!/usr/bin/env python3
"""
Updated Agentic Pipeline: Fast and accurate actor identification using InsightFace + pgvector.

Key improvements:
1. Uses InsightFace for face recognition (much faster than vision LLMs)
2. Fetches cast from TMDB API based on movie/series name
3. Downloads and caches actor profile images locally
4. Stores face embeddings in PostgreSQL with pgvector for fast similarity search
5. Only matches against cast members of the specific movie/series
6. Falls back to YOLO for basic object detection

Input/Output format matches agentic_pipeline.py for compatibility.
"""

import cv2
import json
import argparse
import os
import requests
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from ultralytics import YOLO
import psycopg2
from psycopg2.extras import execute_values
import hashlib
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from logging_config import get_logger
logger = get_logger("pipeline")


class TMDBCastFetcher:
    """Fetches cast information from TMDB API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError(
                "TMDB API key required. Set TMDB_API_KEY environment variable.\n"
                "Get free API key at: https://www.themoviedb.org/settings/api"
            )
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.cache_dir = Path("cache/tmdb/actors")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("TMDB cache dir", extra={"detail": str(self.cache_dir.absolute())})
    
    def search_title(self, title: str, media_type: str = None) -> Optional[Dict]:
        """Search for movie or TV series by title."""
        logger.info("Searching TMDB", extra={"step": "tmdb", "movie": title})
        
        # Try multi search first
        url = f"{self.base_url}/search/multi"
        params = {
            'api_key': self.api_key,
            'query': title,
            'language': 'en-US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                # Filter by media type if specified
                results = data['results']
                if media_type:
                    results = [r for r in results if r.get('media_type') == media_type]
                
                if results:
                    result = results[0]
                    logger.info("TMDB title found", extra={
                        "step": "tmdb",
                        "movie": result.get('title') or result.get('name'),
                        "detail": result.get('media_type')
                    })
                    return result
            
            logger.warning("TMDB title not found", extra={"step": "tmdb", "movie": title})
            return None
        except Exception as e:
            logger.error("TMDB search failed", extra={"step": "tmdb", "error": str(e)})
            return None
    
    def get_cast(self, tmdb_id: int, media_type: str, max_cast: int = 20) -> List[Dict]:
        """Get cast list for a movie or TV series."""
        logger.info("Fetching cast", extra={"step": "tmdb", "detail": f"{media_type} ID {tmdb_id}"})
        
        url = f"{self.base_url}/{media_type}/{tmdb_id}/credits"
        params = {
            'api_key': self.api_key,
            'language': 'en-US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            cast_list = []
            for member in data.get('cast', [])[:max_cast]:
                cast_list.append({
                    'id': member['id'],
                    'name': member['name'],
                    'character': member.get('character'),
                    'profile_path': member.get('profile_path'),
                    'order': member.get('order', 999)
                })
            
            logger.info("Cast loaded", extra={"step": "tmdb", "count": len(cast_list)})
            return cast_list
        except Exception as e:
            logger.error("Cast fetch failed", extra={"step": "tmdb", "error": str(e)})
            return []
    
    def get_actor_images(self, actor_id: int, max_images: int = 5) -> List[str]:
        """Get profile images for an actor."""
        url = f"{self.base_url}/person/{actor_id}/images"
        params = {'api_key': self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            image_urls = []
            for profile in data.get('profiles', [])[:max_images]:
                if profile.get('file_path'):
                    image_urls.append(f"{self.image_base_url}{profile['file_path']}")
            
            return image_urls
        except Exception as e:
            logger.warning("Actor images fetch failed", extra={"step": "tmdb", "error": str(e), "detail": f"actor {actor_id}"})
            return []
    
    def download_image(self, url: str, save_path: Path, max_retries: int = 3) -> bool:
        """Download image from URL with retry logic."""
        import time
        
        for attempt in range(max_retries):
            try:
                # Increase timeout and add stream for large images
                response = requests.get(url, timeout=30, stream=True)
                response.raise_for_status()
                
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write in chunks for large images
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning("Image download timeout, retrying", extra={"step": "tmdb", "detail": f"attempt {attempt + 2}/{max_retries}"})
                    time.sleep(wait_time)
                else:
                    logger.error("Image download timeout", extra={"step": "tmdb", "error": f"timeout after {max_retries} attempts"})
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("Image download error, retrying", extra={"step": "tmdb", "error": str(e)})
                    time.sleep(2)
                else:
                    logger.error("Image download failed", extra={"step": "tmdb", "error": str(e), "detail": f"after {max_retries} attempts"})
                    return False
        
        return False
    
    def cache_actor_images(self, actor_id: int, actor_name: str, max_images: int = 5) -> List[str]:
        """Download and cache actor profile images."""
        actor_dir = self.cache_dir / f"actor_{actor_id}_{actor_name.replace(' ', '_')}"
        actor_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already cached
        existing_images = list(actor_dir.glob("*.jpg"))
        if existing_images:
            logger.debug("Using cached actor images", extra={"actor": actor_name, "count": len(existing_images)})
            return [str(p) for p in existing_images]
        
        # Download new images
        logger.info("Downloading actor images", extra={"step": "tmdb", "actor": actor_name})
        image_urls = self.get_actor_images(actor_id, max_images)
        
        cached_paths = []
        for idx, url in enumerate(image_urls):
            save_path = actor_dir / f"profile_{idx}.jpg"
            if self.download_image(url, save_path):
                cached_paths.append(str(save_path))
        
        logger.info("Actor images cached", extra={"actor": actor_name, "count": len(cached_paths)})
        return cached_paths


class FaceEmbeddingDB:
    """PostgreSQL database with pgvector for face embeddings."""
    
    def __init__(self, db_config: Dict = None):
        """Initialize database connection."""
        if db_config is None:
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'face_recognition'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
            }
        
        self.db_config = db_config
        self.conn = None
        self._connect()
        self._init_tables()
    
    def _connect(self):
        """Connect to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to PostgreSQL", extra={"step": "db"})
        except Exception as e:
            logger.error("Database connection failed", extra={"step": "db", "error": str(e)})
            raise
    
    def _init_tables(self):
        """Initialize database tables with pgvector extension."""
        with self.conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create embeddings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id SERIAL PRIMARY KEY,
                    actor_id INTEGER NOT NULL,
                    actor_name VARCHAR(255) NOT NULL,
                    image_path TEXT NOT NULL,
                    embedding vector(512),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(actor_id, image_path)
                );
            """)
            
            # Create index for faster similarity search
            # Use HNSW for better performance on small-medium datasets
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS face_embeddings_vector_idx 
                    ON face_embeddings USING hnsw (embedding vector_cosine_ops);
                """)
            except Exception:
                # Fallback to IVFFlat if HNSW not available
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS face_embeddings_vector_idx 
                    ON face_embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
            
            self.conn.commit()
            logger.info("Database tables initialized", extra={"step": "db"})
    
    def store_embedding(self, actor_id: int, actor_name: str, 
                       image_path: str, embedding: np.ndarray):
        """Store face embedding in database."""
        with self.conn.cursor() as cur:
            # Convert numpy array to list for pgvector
            embedding_list = embedding.tolist()
            
            cur.execute("""
                INSERT INTO face_embeddings (actor_id, actor_name, image_path, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (actor_id, image_path) DO UPDATE
                SET embedding = EXCLUDED.embedding;
            """, (actor_id, actor_name, image_path, embedding_list))
            
            self.conn.commit()
    
    def search_similar(self, embedding: np.ndarray, actor_ids: List[int] = None,
                      threshold: float = 0.6, limit: int = 5, debug: bool = False) -> List[Dict]:
        """Search for similar faces using cosine similarity."""
        with self.conn.cursor() as cur:
            embedding_list = embedding.tolist()
            
            if debug:
                logger.debug("Face search params", extra={"step": "face", "detail": f"dim={len(embedding_list)} threshold={threshold}"})
            
            # Debug: Check if actors exist in database
            if debug and actor_ids:
                placeholders_debug = ','.join(['%s'] * len(actor_ids))
                cur.execute(f"""
                    SELECT actor_id, actor_name, COUNT(*) 
                    FROM face_embeddings 
                    WHERE actor_id IN ({placeholders_debug})
                    GROUP BY actor_id, actor_name;
                """, tuple(actor_ids))
                found_actors = cur.fetchall()
                if not found_actors:
                    logger.warning("No embeddings found for cast", extra={"step": "face", "detail": f"actor IDs: {actor_ids[:5]}"})
                else:
                    logger.debug("Actors with embeddings", extra={"step": "face", "count": len(found_actors)})
            
            # Build query with optional actor filter
            if actor_ids:
                placeholders = ','.join(['%s'] * len(actor_ids))
                query = f"""
                    SELECT actor_id, actor_name, image_path,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM face_embeddings
                    WHERE actor_id IN ({placeholders})
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                params = [embedding_list] + list(actor_ids) + [embedding_list, limit]
            else:
                query = """
                    SELECT actor_id, actor_name, image_path,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM face_embeddings
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                params = [embedding_list, embedding_list, limit]
            
            try:
                cur.execute(query, params)
                rows = cur.fetchall()
                
                if debug:
                    logger.debug("Face query results", extra={"step": "face", "count": len(rows)})
                
            except Exception as e:
                logger.error("Face query failed", extra={"step": "face", "error": str(e)})
                return []
            
            all_results = []
            results = []
            for row in rows:
                actor_id, actor_name, image_path, similarity = row
                result = {
                    'actor_id': actor_id,
                    'actor_name': actor_name,
                    'image_path': image_path,
                    'similarity': float(similarity),
                    'confidence': int(similarity * 100)
                }
                all_results.append(result)
                if similarity >= threshold:
                    results.append(result)
            
            if debug and all_results:
                top_matches = ", ".join(f"{r['actor_name']}:{r['confidence']}%" for r in all_results[:3])
                logger.info("Face match results", extra={"step": "face", "detail": top_matches})
            
            return results
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


class InsightFaceRecognizer:
    """Face recognition using InsightFace."""
    
    def __init__(self):
        """Initialize InsightFace model."""
        try:
            from insightface.app import FaceAnalysis
            
            logger.info("Loading InsightFace model", extra={"step": "init"})
            self.app = FaceAnalysis(providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("InsightFace model loaded", extra={"step": "init"})
        except ImportError:
            raise ImportError(
                "InsightFace not installed. Install with: pip install insightface onnxruntime"
            )
    
    def extract_embedding(self, image_path: str, debug: bool = False) -> Optional[np.ndarray]:
        """Extract face embedding from image."""
        img = cv2.imread(image_path)
        if img is None:
            logger.debug("Could not read image", extra={"step": "face", "detail": image_path})
            return None
        
        faces = self.app.get(img)
        if not faces:
            logger.debug("No face detected", extra={"step": "face", "detail": Path(image_path).name})
            return None
        
        # Return embedding of first/largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        if debug:
            logger.debug("Face detected", extra={"step": "face", "detail": f"{int(face.bbox[2]-face.bbox[0])}x{int(face.bbox[3]-face.bbox[1])}"})
        
        return face.embedding
    
    def extract_embeddings_from_crop(self, image: np.ndarray, debug: bool = False) -> Optional[np.ndarray]:
        """Extract face embedding from cropped image array."""
        if image is None or image.size == 0:
            logger.debug("Invalid image array", extra={"step": "face"})
            return None
        
        faces = self.app.get(image)
        if not faces:
            if debug:
                h, w = image.shape[:2]
                logger.debug("No face in crop", extra={"step": "face", "detail": f"{w}x{h}"})
            return None
        
        # Return embedding of first/largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        if debug:
            logger.debug("Face detected in crop", extra={"step": "face", "detail": f"{int(face.bbox[2]-face.bbox[0])}x{int(face.bbox[3]-face.bbox[1])}"})
        
        return face.embedding


class UpdatedAgenticPipeline:
    """Fast and accurate pipeline using InsightFace + pgvector."""
    
    def __init__(self, yolo_model: str = "yolov8n.pt", vision_model: str = None, 
                 use_vision_analysis: bool = False):
        """Initialize pipeline components."""
        self.yolo = YOLO(yolo_model)
        self.tmdb = TMDBCastFetcher()
        self.face_recognizer = InsightFaceRecognizer()
        self.db = FaceEmbeddingDB()
        self.use_vision_analysis = use_vision_analysis
        self.vision_model = vision_model
        
        # Initialize vision model if requested
        if use_vision_analysis:
            try:
                import ollama
                # Route through llm-replay proxy if configured
                replay_host = os.getenv('LLM_REPLAY_HOST')
                if replay_host:
                    self.ollama = ollama.Client(host=replay_host)
                    logger.info("LLM Replay proxy configured", extra={"step": "init", "detail": replay_host})
                else:
                    self.ollama = ollama
                self.vision_model = vision_model or "llama3.2-vision:11b"
                logger.info("Vision model enabled", extra={"step": "init", "detail": self.vision_model})
                
                # Load prompts
                prompts_file = Path(__file__).parent / "prompts_context.json"
                if prompts_file.exists():
                    with open(prompts_file, 'r') as f:
                        self.prompts = json.load(f)
                else:
                    self.prompts = self._get_default_prompts()
            except ImportError:
                logger.warning("Ollama not installed, vision analysis disabled", extra={"step": "init"})
                self.use_vision_analysis = False
    
    def prepare_movie_cast(self, movie_title: str, media_type: str = None,
                          max_cast: int = 20, images_per_actor: int = 5) -> Optional[Dict]:
        """Prepare cast data for a movie/series."""
        logger.info("Preparing cast data", extra={"step": "cast", "movie": movie_title})
        
        # Search for title
        title_data = self.tmdb.search_title(movie_title, media_type)
        if not title_data:
            return None
        
        tmdb_id = title_data['id']
        media_type = title_data['media_type']
        
        # Get cast
        cast_list = self.tmdb.get_cast(tmdb_id, media_type, max_cast)
        if not cast_list:
            return None
        
        # Download images and generate embeddings
        logger.info("Processing cast members", extra={"step": "cast", "count": len(cast_list)})
        
        processed_cast = []
        for idx, member in enumerate(cast_list, 1):
            actor_id = member['id']
            actor_name = member['name']
            
            logger.debug("Processing actor", extra={"step": "cast", "actor": actor_name, "detail": f"{idx}/{len(cast_list)}"})
            
            # Cache images
            image_paths = self.tmdb.cache_actor_images(
                actor_id, actor_name, images_per_actor
            )
            
            if not image_paths:
                logger.warning("No images found for actor", extra={"step": "cast", "actor": actor_name})
                continue
            
            # Check if embeddings already exist in database
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM face_embeddings WHERE actor_id = %s;
                """, (actor_id,))
                existing_count = cur.fetchone()[0]
            
            if existing_count > 0:
                logger.debug("Actor has existing embeddings", extra={"actor": actor_name, "count": existing_count})
                processed_cast.append(member)
            else:
                # Generate and store embeddings
                embeddings_stored = 0
                for img_path in image_paths:
                    embedding = self.face_recognizer.extract_embedding(img_path, debug=True)
                    if embedding is not None:
                        self.db.store_embedding(actor_id, actor_name, img_path, embedding)
                        embeddings_stored += 1
                
                if embeddings_stored > 0:
                    logger.info("Stored face embeddings", extra={"step": "cast", "actor": actor_name, "count": embeddings_stored})
                    processed_cast.append(member)
                else:
                    logger.warning("No faces detected for actor", extra={"step": "cast", "actor": actor_name, "detail": f"{len(image_paths)} images tried"})
        
        movie_context = {
            'title': title_data.get('title') or title_data.get('name'),
            'tmdb_id': tmdb_id,
            'media_type': media_type,
            'year': (title_data.get('release_date') or title_data.get('first_air_date', ''))[:4],
            'cast': processed_cast
        }
        
        logger.info("Cast preparation complete", extra={"step": "cast", "count": len(processed_cast), "movie": movie_context['title']})
        return movie_context
    
    def detect_all_objects(self, image_path: str, min_confidence: float = 0.5) -> Dict:
        """Detect all objects in image using YOLO."""
        logger.info("Running YOLO detection", extra={"step": "detect"})
        
        results = self.yolo(image_path)
        detections = {
            'people': [],
            'products': [],
            'animals': [],
            'vehicles': [],
            'electronics': [],
            'furniture': [],
            'other': []
        }
        
        # Category mappings (same as agentic_pipeline.py)
        animal_classes = {'dog', 'cat', 'bird', 'horse', 'sheep', 'cow', 'elephant', 
                         'bear', 'zebra', 'giraffe'}
        vehicle_classes = {'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 
                          'boat', 'bicycle'}
        product_classes = {'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 
                          'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli',
                          'carrot', 'hot dog', 'pizza', 'donut', 'cake'}
        electronics_classes = {'tv', 'laptop', 'mouse', 'remote', 'keyboard', 
                              'cell phone', 'microwave', 'oven', 'toaster'}
        furniture_classes = {'chair', 'couch', 'bed', 'dining table', 'toilet', 
                            'potted plant'}
        
        # Use stricter threshold for people, lower for objects
        # (small objects in movie frames often have lower YOLO confidence)
        object_min_confidence = min(min_confidence, 0.3)
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                confidence = float(box.conf[0])
                
                threshold = min_confidence if cls_name == 'person' else object_min_confidence
                if confidence < threshold:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                detection = {
                    'class': cls_name,
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': confidence
                }
                
                if cls_name == 'person':
                    detections['people'].append(detection)
                elif cls_name in animal_classes:
                    detections['animals'].append(detection)
                elif cls_name in vehicle_classes:
                    detections['vehicles'].append(detection)
                elif cls_name in product_classes:
                    detections['products'].append(detection)
                elif cls_name in electronics_classes:
                    detections['electronics'].append(detection)
                elif cls_name in furniture_classes:
                    detections['furniture'].append(detection)
                else:
                    detections['other'].append(detection)
        
        total = sum(len(v) for v in detections.values())
        summary = {k: len(v) for k, v in detections.items() if v}
        logger.info("YOLO detection complete", extra={"step": "detect", "count": total, "detail": str(summary)})
        
        return detections
    
    def detect_people(self, image_path: str, min_confidence: float = 0.5) -> List[Dict]:
        """Detect people in image using YOLO."""
        all_detections = self.detect_all_objects(image_path, min_confidence)
        return all_detections['people']
    
    def _get_default_prompts(self) -> Dict:
        """Get default prompts if prompts_context.json not found."""
        return {
            'scene_analysis': {
                'prompt': 'Analyze this image and provide: setting, lighting, time_of_day, mood, background_elements (as array), composition, and context. Return as JSON.'
            },
            'person': {
                'describe': {
                    'prompt': 'Describe this person in detail: gender, facial_features, clothing (description, colors as array, style, accessories as array), pose, expression, held_items as array. Return as JSON.'
                }
            },
            'product': {
                'prompt': 'Analyze this product: brand (or null), product_type, size, material, color (as array), label_text (or null), condition, distinctive_features. Return as JSON.'
            },
            'animal': {
                'prompt': 'Analyze this animal: breed, size, color (as array), age_estimate, activity, distinctive_features. Return as JSON.'
            },
            'vehicle': {
                'prompt': 'Analyze this vehicle: make (or null), model (or null), year_range, color, body_type, condition. Return as JSON.'
            },
            'electronics': {
                'prompt': 'Analyze this electronic device: brand (or null), model (or null), type, color, condition. Return as JSON.'
            },
            'furniture': {
                'prompt': 'Analyze this furniture: type, material, style, color (as array), condition. Return as JSON.'
            },
            'default': {
                'prompt': 'Analyze this {object_type}: type, brand (or null), color (as array), material, condition, distinctive_features, context. Return as JSON.'
            }
        }
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for vision model."""
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _parse_json_response(self, content: str) -> Dict:
        """Parse JSON from LLM response."""
        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            return json.loads(content)
        except Exception:
            return {}
    
    def analyze_scene_with_vision(self, image_path: str) -> Dict:
        """Analyze scene using vision model."""
        if not self.use_vision_analysis:
            return {
                'setting': 'Not analyzed',
                'lighting': 'Not analyzed',
                'time_of_day': 'Not analyzed',
                'mood': 'Not analyzed',
                'background_elements': [],
                'composition': 'Not analyzed',
                'context': 'Fast mode - scene analysis skipped'
            }
        
        logger.info("Analyzing scene with vision model", extra={"step": "scene"})
        image_data = self._encode_image(image_path)
        prompt = self.prompts['scene_analysis']['prompt']
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        result = self._parse_json_response(response['message']['content'])
        return result if result else {
            'setting': 'Unknown',
            'lighting': 'Unknown',
            'time_of_day': 'Unknown',
            'mood': 'Unknown',
            'background_elements': [],
            'composition': 'Unknown',
            'context': 'Analysis failed'
        }
    
    def analyze_person_details(self, crop_path: str) -> Dict:
        """Analyze person details using vision model."""
        if not self.use_vision_analysis:
            return {
                'gender': 'unknown',
                'facial_features': 'Not analyzed',
                'clothing': {
                    'description': 'Not analyzed',
                    'colors': [],
                    'style': 'Not analyzed',
                    'accessories': []
                },
                'pose': 'Not analyzed',
                'expression': 'Not analyzed',
                'held_items': []
            }
        
        image_data = self._encode_image(crop_path)
        prompt = self.prompts['person']['describe']['prompt']
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        result = self._parse_json_response(response['message']['content'])
        
        # Ensure proper structure
        if not result.get('clothing'):
            result['clothing'] = {
                'description': 'Not analyzed',
                'colors': [],
                'style': 'Not analyzed',
                'accessories': []
            }
        if not result.get('held_items'):
            result['held_items'] = []
        
        return result
    
    def analyze_object(self, crop_path: str, object_class: str, category: str,
                       scene_context: Dict = None) -> Dict:
        """Analyze any object using vision model, with scene context for accuracy."""
        if not self.use_vision_analysis:
            return None
        
        image_data = self._encode_image(crop_path)
        
        # Get appropriate prompt
        if category in self.prompts:
            prompt = self.prompts[category]['prompt']
        else:
            prompt = self.prompts['default']['prompt'].format(object_type=object_class)
        
        # Inject scene context so the vision model can override YOLO's label
        if scene_context:
            scene_desc = scene_context.get('context', '')
            if scene_desc:
                prompt = (
                    f"IMPORTANT CONTEXT: The overall scene shows: \"{scene_desc}\". "
                    f"The object detector labeled this crop as \"{object_class}\", but that may be wrong. "
                    f"Look at the crop carefully and use the scene context to determine what this object actually is. "
                    f"If the detector's label is wrong, describe the actual object instead.\n\n"
                    + prompt
                )
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        result = self._parse_json_response(response['message']['content'])
        return result if result else {}
    
    def crop_person(self, image_path: str, bbox: Tuple, padding: float = 0.2) -> np.ndarray:
        """Crop person from image with padding."""
        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        
        x1, y1, x2, y2 = bbox
        
        # Add padding
        width = x2 - x1
        height = y2 - y1
        pad_x = int(width * padding)
        pad_y = int(height * padding)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        return img[y1:y2, x1:x2]

    def detect_faces_direct(self, image_path: str, output_dir: str,
                            cast_actor_ids: List[int],
                            similarity_threshold: float = 0.6) -> List[Dict]:
        """Detect and identify faces directly with InsightFace on the full image.

        Returns a list of person dicts (same schema as the YOLO-based flow)
        with one entry per detected face.
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.error("Could not read image for face detection", extra={"step": "identify"})
            return []

        faces = self.face_recognizer.app.get(img)
        logger.info("InsightFace detected faces", extra={"step": "identify", "count": len(faces)})

        if not faces:
            return []

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        input_name = Path(image_path).stem
        h, w = img.shape[:2]

        people = []
        for idx, face in enumerate(faces, 1):
            # Crop face region with padding for the vision model
            x1, y1, x2, y2 = [int(c) for c in face.bbox]
            fw, fh = x2 - x1, y2 - y1
            pad = 0.6  # generous padding so crop shows upper body / clothing
            cx1 = max(0, int(x1 - fw * pad))
            cy1 = max(0, int(y1 - fh * pad))
            cx2 = min(w, int(x2 + fw * pad))
            cy2 = min(h, int(y2 + fh * 1.5))  # more padding below for body
            cropped = img[cy1:cy2, cx1:cx2]

            crop_filename = f"{input_name}_person_{idx}.png"
            crop_path = output_path / crop_filename
            cv2.imwrite(str(crop_path), cropped)

            # Match embedding against cast
            embedding = face.embedding
            matches = self.db.search_similar(
                embedding,
                actor_ids=cast_actor_ids,
                threshold=similarity_threshold,
                limit=5,
                debug=True
            )
            match = matches[0] if matches else None

            det_confidence = float(face.det_score) if hasattr(face, 'det_score') else 1.0

            people.append({
                'match': match,
                'crop_path': str(crop_path),
                'detection_confidence': det_confidence,
                'bbox': (x1, y1, x2, y2),
            })

            if match:
                logger.info("Person identified", extra={
                    "step": "identify", "actor": match['actor_name'],
                    "detail": f"{match['confidence']}%"
                })
            else:
                logger.info("Person not matched", extra={
                    "step": "identify", "detail": f"person {idx} below threshold"
                })

        return people
    
    def identify_person(self, cropped_image: np.ndarray, cast_actor_ids: List[int],
                       similarity_threshold: float = 0.6, debug: bool = True) -> Optional[Dict]:
        """Identify person using face recognition."""
        embedding = self.face_recognizer.extract_embeddings_from_crop(cropped_image)
        if embedding is None:
            logger.debug("No face detected in crop", extra={"step": "identify"})
            return None
        
        logger.debug("Face embedding extracted", extra={"step": "identify", "detail": f"dim={len(embedding)}"})
        logger.debug("Searching cast", extra={"step": "identify", "count": len(cast_actor_ids)})
        
        matches = self.db.search_similar(
            embedding,
            actor_ids=cast_actor_ids,
            threshold=similarity_threshold,
            limit=5,
            debug=debug
        )
        
        if matches:
            return matches[0]
        
        # If no match, check entire database for diagnostics
        if debug:
            logger.debug("No cast match, checking full database", extra={"step": "identify"})
            all_matches = self.db.search_similar(
                embedding,
                actor_ids=None,
                threshold=0.0,
                limit=5,
                debug=False
            )
            
            if all_matches:
                best = all_matches[0]
                in_cast = best['actor_id'] in cast_actor_ids
                logger.info("Best global match", extra={
                    "step": "identify",
                    "actor": best['actor_name'],
                    "detail": f"{best['confidence']}% {'(in cast)' if in_cast else '(not in cast)'}"
                })
            else:
                logger.warning("No embeddings in database", extra={"step": "identify"})
        
        return None
    
    def _process_objects(self, image_path: str, detections: List[Dict], 
                        category: str, output_path: Path, scene_context: Dict) -> List[Dict]:
        """Process detected objects with vision model analysis."""
        if not detections or not self.use_vision_analysis:
            return []
        
        logger.info("Processing objects with vision", extra={"step": "objects", "count": len(detections), "detail": category})
        
        results = []
        img = cv2.imread(image_path)
        
        for idx, detection in enumerate(detections, 1):
            # Crop object
            x1, y1, x2, y2 = detection['bbox']
            
            # Add padding
            h, w = img.shape[:2]
            pad = 0.1
            width = x2 - x1
            height = y2 - y1
            x1 = max(0, int(x1 - width * pad))
            y1 = max(0, int(y1 - height * pad))
            x2 = min(w, int(x2 + width * pad))
            y2 = min(h, int(y2 + height * pad))
            
            cropped = img[y1:y2, x1:x2]
            
            # Save crop
            input_name = Path(image_path).stem
            crop_filename = f"{input_name}_{category}_{idx}.png"
            crop_path = output_path / crop_filename
            cv2.imwrite(str(crop_path), cropped)
            
            # Analyze with vision model
            analysis = self.analyze_object(str(crop_path), detection['class'], category,
                                           scene_context=scene_context)
            
            if analysis:
                analysis['object_class'] = detection['class']
                analysis['crop_image'] = str(crop_path)
                analysis['detection_confidence'] = detection['confidence']
                results.append(analysis)
                logger.debug("Object analyzed", extra={"step": "objects", "detail": f"{detection['class']} {idx}"})
        
        return results
    
    def process_image(self, image_path: str, movie_title: str,
                     output_dir: str = "output",
                     similarity_threshold: float = 0.6) -> Dict:
        """Process image with fast face recognition pipeline."""
        logger.info("Pipeline started", extra={"step": "start", "movie": movie_title, "image_url": Path(image_path).name})
        
        # Prepare cast data
        movie_context = self.prepare_movie_cast(movie_title)
        if not movie_context:
            logger.error("Failed to prepare cast data", extra={"step": "cast", "movie": movie_title})
            return None
        
        cast_actor_ids = [member['id'] for member in movie_context['cast']]
        
        logger.info("Cast prepared", extra={"step": "cast", "count": len(cast_actor_ids)})
        
        # Detect all objects
        all_detections = self.detect_all_objects(image_path)
        
        if not all_detections['people']:
            logger.warning("No people detected in image", extra={"step": "detect"})
        
        # Process each detected person
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        identified_people = []
        
        if all_detections['people']:
            logger.info("Identifying people", extra={"step": "identify", "count": len(all_detections['people'])})
        
        for idx, detection in enumerate(all_detections['people'], 1):
            logger.debug("Processing person", extra={"step": "identify", "detail": f"{idx}/{len(all_detections['people'])}"})
            
            # Crop person
            cropped = self.crop_person(image_path, detection['bbox'])
            
            # Save crop
            input_name = Path(image_path).stem
            crop_filename = f"{input_name}_person_{idx}.png"
            crop_path = output_path / crop_filename
            cv2.imwrite(str(crop_path), cropped)
            
            # Identify
            match = self.identify_person(cropped, cast_actor_ids, similarity_threshold)
            
            # Analyze person details with vision model (if enabled)
            if self.use_vision_analysis:
                logger.debug("Analyzing person with vision model", extra={"step": "identify", "detail": f"person {idx}"})
                vision_details = self.analyze_person_details(str(crop_path))
            else:
                vision_details = {}
            
            if match:
                logger.info("Person identified", extra={
                    "step": "identify", "actor": match['actor_name'],
                    "detail": f"{match['confidence']}% matched to {Path(match['image_path']).name}"
                })
                
                # Find cast member details
                cast_member = next(
                    (m for m in movie_context['cast'] if m['id'] == match['actor_id']),
                    None
                )
                
                person_data = {
                    'name': match['actor_name'],
                    'profession': 'Actor',
                    'character': cast_member['character'] if cast_member else None,
                    'confidence': match['confidence'],
                    'similarity_score': match['similarity'],
                    'matched_image': match['image_path'],
                    'gender': vision_details.get('gender', 'unknown'),
                    'facial_features': vision_details.get('facial_features', 'Identified via face recognition'),
                    'clothing': vision_details.get('clothing', {
                        'description': 'Not analyzed',
                        'colors': [],
                        'style': 'Not analyzed',
                        'accessories': []
                    }),
                    'pose': vision_details.get('pose', 'Not analyzed'),
                    'expression': vision_details.get('expression', 'Not analyzed'),
                    'held_items': vision_details.get('held_items', []),
                    'object_class': 'person',
                    'crop_image': str(crop_path),
                    'detection_confidence': detection['confidence']
                }
            else:
                logger.info("Unknown person", extra={"step": "identify", "detail": f"person {idx} below threshold"})
                person_data = {
                    'name': None,
                    'profession': None,
                    'character': None,
                    'confidence': 0,
                    'gender': 'unknown',
                    'facial_features': 'Face detected but not identified',
                    'clothing': {
                        'description': 'Not analyzed',
                        'colors': [],
                        'style': 'Not analyzed',
                        'accessories': []
                    },
                    'pose': 'Not analyzed',
                    'expression': 'Not analyzed',
                    'held_items': [],
                    'object_class': 'person',
                    'crop_image': str(crop_path),
                    'detection_confidence': detection['confidence']
                }
            
            identified_people.append(person_data)
        
        # Analyze scene (if vision model enabled)
        logger.info("Running scene analysis", extra={"step": "scene"})
        scene_analysis = self.analyze_scene_with_vision(image_path)
        
        # Build result matching agentic_pipeline.py output format
        result = {
            'source_image': Path(image_path).name,
            'movie_context': {
                'title': movie_context['title'],
                'year': movie_context['year'],
                'cast': [m['name'] for m in movie_context['cast']]
            },
            'scene_analysis': scene_analysis,
            'detections_summary': {
                'people': len(identified_people),
                'products': len(all_detections['products']),
                'animals': len(all_detections['animals']),
                'vehicles': len(all_detections['vehicles']),
                'electronics': len(all_detections['electronics']),
                'furniture': len(all_detections['furniture']),
                'other_objects': len(all_detections['other'])
            },
            'people': identified_people,
            'products': [],  # Will be filled if vision analysis enabled
            'animals': [],
            'vehicles': [],
            'electronics': [],
            'furniture': [],
            'other_objects': []
        }
        
        # Process other object categories if vision analysis enabled
        if self.use_vision_analysis:
            result['products'] = self._process_objects(
                image_path, all_detections['products'], 'products', output_path, scene_analysis
            )
            result['animals'] = self._process_objects(
                image_path, all_detections['animals'], 'animal', output_path, scene_analysis
            )
            result['vehicles'] = self._process_objects(
                image_path, all_detections['vehicles'], 'vehicle', output_path, scene_analysis
            )
            result['electronics'] = self._process_objects(
                image_path, all_detections['electronics'], 'electronics', output_path, scene_analysis
            )
            result['furniture'] = self._process_objects(
                image_path, all_detections['furniture'], 'furniture', output_path, scene_analysis
            )
            result['other_objects'] = self._process_objects(
                image_path, all_detections['other'], 'default', output_path, scene_analysis
            )
        
        # Save result
        result_file = output_path / f"{Path(image_path).stem}_complete_analysis.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        identified_count = len([p for p in identified_people if p['name']])
        logger.info("Pipeline complete", extra={
            "step": "done", "movie": movie_context['title'],
            "detail": f"identified {identified_count}/{len(identified_people)} people"
        })
        
        return result
    
    def close(self):
        """Cleanup resources."""
        self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Updated Agentic Pipeline - Fast face recognition with InsightFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Identify actors in an image from a movie
  python3 updated_agentic_pipeline.py input/srk_test.jpeg --movie "Pathaan"
  
  # Specify output directory
  python3 updated_agentic_pipeline.py input/leo_test.webp --movie "Leo" -o output
  
  # Adjust similarity threshold (default 0.6)
  python3 updated_agentic_pipeline.py input/rdj.jpg --movie "Iron Man" --threshold 0.7

Requirements:
  - PostgreSQL with pgvector extension installed
  - TMDB API key (set TMDB_API_KEY environment variable)
  - InsightFace: pip install insightface onnxruntime
  
Database setup:
  1. Install PostgreSQL and pgvector
  2. Create database: createdb face_recognition
  3. Set environment variables (or use defaults):
     export POSTGRES_HOST=localhost
     export POSTGRES_PORT=5432
     export POSTGRES_DB=face_recognition
     export POSTGRES_USER=postgres
     export POSTGRES_PASSWORD=postgres
        """
    )
    parser.add_argument("image", help="Input image file")
    parser.add_argument("--movie", required=True, help="Movie or series title")
    parser.add_argument("-o", "--output", default="output",
                       help="Output directory (default: output)")
    parser.add_argument("--yolo-model", default="yolov8n.pt",
                       help="YOLO model (default: yolov8n.pt)")
    parser.add_argument("--threshold", type=float, default=0.6,
                       help="Face similarity threshold 0-1 (default: 0.6, lower=more lenient)")
    parser.add_argument("--max-cast", type=int, default=20,
                       help="Maximum cast members to process (default: 20)")
    parser.add_argument("--images-per-actor", type=int, default=5,
                       help="Profile images per actor (default: 5)")
    parser.add_argument("--show-all-matches", action="store_true",
                       help="Show all similarity scores even below threshold")
    parser.add_argument("--vision-model", default="qwen3-vl:8b",
                       help="Vision model for scene/clothing analysis (default: llama3.2-vision:11b)")
    parser.add_argument("--enable-vision", action="store_true",
                       help="Enable vision model for full analysis: scene, clothing, products, animals, etc. (slower but complete)")
    
    args = parser.parse_args()
    
    try:
        pipeline = UpdatedAgenticPipeline(
            args.yolo_model,
            vision_model=args.vision_model,
            use_vision_analysis=args.enable_vision
        )
        
        result = pipeline.process_image(
            args.image,
            args.movie,
            args.output,
            args.threshold
        )
        
        pipeline.close()
        
        if not result:
            exit(1)
    
    except Exception as e:
        logger.exception("Pipeline error", extra={"error": str(e)})
        exit(1)


if __name__ == "__main__":
    main()
