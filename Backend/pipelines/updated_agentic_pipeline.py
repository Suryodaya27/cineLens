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
        print(f"📁 Actor images cache directory: {self.cache_dir.absolute()}")
    
    def search_title(self, title: str, media_type: str = None) -> Optional[Dict]:
        """Search for movie or TV series by title."""
        print(f"🔍 Searching TMDB for: {title}")
        
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
                    print(f"✓ Found: {result.get('title') or result.get('name')} "
                          f"({result.get('media_type')})")
                    return result
            
            print(f"❌ Title not found: {title}")
            return None
        except Exception as e:
            print(f"❌ Error searching TMDB: {e}")
            return None
    
    def get_cast(self, tmdb_id: int, media_type: str, max_cast: int = 20) -> List[Dict]:
        """Get cast list for a movie or TV series."""
        print(f"👥 Fetching cast for {media_type} ID {tmdb_id}...")
        
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
            
            print(f"✓ Found {len(cast_list)} cast members")
            return cast_list
        except Exception as e:
            print(f"❌ Error fetching cast: {e}")
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
            print(f"  ⚠️  Error fetching images for actor {actor_id}: {e}")
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
                    wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                    print(f"  ⏱️  Timeout, retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"  ⚠️  Timeout after {max_retries} attempts")
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Error: {e}, retrying...")
                    time.sleep(2)
                else:
                    print(f"  ⚠️  Failed after {max_retries} attempts: {e}")
                    return False
        
        return False
    
    def cache_actor_images(self, actor_id: int, actor_name: str, max_images: int = 5) -> List[str]:
        """Download and cache actor profile images."""
        actor_dir = self.cache_dir / f"actor_{actor_id}_{actor_name.replace(' ', '_')}"
        actor_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already cached
        existing_images = list(actor_dir.glob("*.jpg"))
        if existing_images:
            print(f"  ✓ Using cached images from: {actor_dir}")
            print(f"    Images: {[p.name for p in existing_images]}")
            return [str(p) for p in existing_images]
        
        # Download new images
        print(f"  📥 Downloading images for {actor_name}...")
        print(f"    Saving to: {actor_dir}")
        image_urls = self.get_actor_images(actor_id, max_images)
        
        cached_paths = []
        for idx, url in enumerate(image_urls):
            save_path = actor_dir / f"profile_{idx}.jpg"
            if self.download_image(url, save_path):
                cached_paths.append(str(save_path))
                print(f"    ✓ Saved: {save_path.name}")
        
        print(f"  ✓ Cached {len(cached_paths)} images in {actor_dir}")
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
            print("✓ Connected to PostgreSQL")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("   Make sure PostgreSQL is running and pgvector extension is installed")
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
            print("✓ Database tables initialized")
    
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
                print(f"    ✓ DEBUG: Embedding type: {type(embedding)}, shape: {embedding.shape if hasattr(embedding, 'shape') else 'N/A'}")
                print(f"    ✓ DEBUG: Embedding list length: {len(embedding_list)}, type: {type(embedding_list)}")
                print(f"    ✓ DEBUG: First 3 values: {embedding_list[:3]}")
            
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
                    print(f"    ⚠️  DEBUG: No embeddings found for actor IDs: {actor_ids[:5]}...")
                else:
                    print(f"    ✓ DEBUG: Found {len(found_actors)} actors with embeddings")
            
            # Build query with optional actor filter
            # Note: We pass embedding twice - once for SELECT, once for ORDER BY
            if actor_ids:
                # Use IN clause with explicit actor IDs
                placeholders = ','.join(['%s'] * len(actor_ids))
                query = f"""
                    SELECT actor_id, actor_name, image_path,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM face_embeddings
                    WHERE actor_id IN ({placeholders})
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                # Build params: [embedding, actor_ids..., embedding, limit]
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
                    print(f"    ✓ DEBUG: Query returned {len(rows)} rows")
                
            except Exception as e:
                if debug:
                    print(f"    ❌ DEBUG: Query failed: {e}")
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
            
            # Debug output
            if debug:
                if all_results:
                    print(f"    Top {len(all_results)} matches:")
                    for i, r in enumerate(all_results, 1):
                        status = "✓" if r['similarity'] >= threshold else "✗"
                        print(f"      {status} {i}. {r['actor_name']}: {r['similarity']:.3f} ({r['confidence']}%)")
                else:
                    print(f"    ⚠️  No embeddings found for the specified cast members")
                    print(f"       Cast may not have been cached properly")
            
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
            
            print("🔧 Loading InsightFace model...")
            self.app = FaceAnalysis(providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            print("✓ InsightFace model loaded")
        except ImportError:
            raise ImportError(
                "InsightFace not installed. Install with: pip install insightface onnxruntime"
            )
    
    def extract_embedding(self, image_path: str, debug: bool = False) -> Optional[np.ndarray]:
        """Extract face embedding from image."""
        img = cv2.imread(image_path)
        if img is None:
            if debug:
                print(f"      ⚠️  Could not read image: {image_path}")
            return None
        
        faces = self.app.get(img)
        if not faces:
            if debug:
                print(f"      ⚠️  No face detected in: {Path(image_path).name}")
            return None
        
        # Return embedding of first/largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        if debug:
            print(f"      ✓ Face detected (size: {int(face.bbox[2]-face.bbox[0])}x{int(face.bbox[3]-face.bbox[1])})")
        
        return face.embedding
    
    def extract_embeddings_from_crop(self, image: np.ndarray, debug: bool = False) -> Optional[np.ndarray]:
        """Extract face embedding from cropped image array."""
        if image is None or image.size == 0:
            if debug:
                print(f"      ⚠️  Invalid image array")
            return None
        
        faces = self.app.get(image)
        if not faces:
            if debug:
                h, w = image.shape[:2]
                print(f"      ⚠️  No face detected in crop (size: {w}x{h})")
            return None
        
        # Return embedding of first/largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        if debug:
            print(f"      ✓ Face detected in crop (size: {int(face.bbox[2]-face.bbox[0])}x{int(face.bbox[3]-face.bbox[1])})")
        
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
                    print(f"✓ LLM Replay proxy: {replay_host}")
                else:
                    self.ollama = ollama
                self.vision_model = vision_model or "llama3.2-vision:11b"
                print(f"✓ Vision model enabled: {self.vision_model}")
                
                # Load prompts
                prompts_file = Path(__file__).parent / "prompts_context.json"
                if prompts_file.exists():
                    with open(prompts_file, 'r') as f:
                        self.prompts = json.load(f)
                else:
                    self.prompts = self._get_default_prompts()
            except ImportError:
                print("⚠️  Ollama not installed. Vision analysis disabled.")
                self.use_vision_analysis = False
    
    def prepare_movie_cast(self, movie_title: str, media_type: str = None,
                          max_cast: int = 20, images_per_actor: int = 5) -> Optional[Dict]:
        """Prepare cast data for a movie/series."""
        print(f"\n{'='*70}")
        print(f"🎬 PREPARING CAST DATA: {movie_title}")
        print(f"{'='*70}\n")
        
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
        print(f"\n📸 Processing {len(cast_list)} cast members...\n")
        
        processed_cast = []
        for idx, member in enumerate(cast_list, 1):
            actor_id = member['id']
            actor_name = member['name']
            
            print(f"[{idx}/{len(cast_list)}] {actor_name}")
            
            # Cache images
            image_paths = self.tmdb.cache_actor_images(
                actor_id, actor_name, images_per_actor
            )
            
            if not image_paths:
                print(f"  ⚠️  No images found, skipping")
                continue
            
            # Check if embeddings already exist in database
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM face_embeddings WHERE actor_id = %s;
                """, (actor_id,))
                existing_count = cur.fetchone()[0]
            
            if existing_count > 0:
                print(f"  ✓ Already has {existing_count} embeddings in database")
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
                    print(f"  ✓ Stored {embeddings_stored}/{len(image_paths)} face embeddings")
                    processed_cast.append(member)
                else:
                    print(f"  ⚠️  No faces detected in any of the {len(image_paths)} images")
        
        movie_context = {
            'title': title_data.get('title') or title_data.get('name'),
            'tmdb_id': tmdb_id,
            'media_type': media_type,
            'year': (title_data.get('release_date') or title_data.get('first_air_date', ''))[:4],
            'cast': processed_cast
        }
        
        print(f"\n✓ Prepared {len(processed_cast)} cast members with face embeddings")
        return movie_context
    
    def detect_all_objects(self, image_path: str, min_confidence: float = 0.5) -> Dict:
        """Detect all objects in image using YOLO."""
        print("🔍 Detecting all objects in image...")
        
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
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                confidence = float(box.conf[0])
                
                if confidence < min_confidence:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                detection = {
                    'class': cls_name,
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': confidence
                }
                
                # Categorize detection
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
        
        # Print summary
        total = sum(len(v) for v in detections.values())
        print(f"✓ Detected {total} objects:")
        for category, items in detections.items():
            if items:
                classes = ', '.join(set(item['class'] for item in items))
                print(f"  • {category.capitalize()}: {len(items)} ({classes})")
        
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
        
        print("  🎬 Analyzing scene with vision model...")
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
    
    def identify_person(self, cropped_image: np.ndarray, cast_actor_ids: List[int],
                       similarity_threshold: float = 0.6, debug: bool = True) -> Optional[Dict]:
        """Identify person using face recognition."""
        # Extract face embedding
        embedding = self.face_recognizer.extract_embeddings_from_crop(cropped_image)
        if embedding is None:
            print(f"    ⚠️  No face detected in cropped image")
            return None
        
        print(f"    ✓ Face embedding extracted (dim: {len(embedding)})")
        
        if debug:
            print(f"    🔍 Searching among {len(cast_actor_ids)} cast members (IDs: {cast_actor_ids[:5]}{'...' if len(cast_actor_ids) > 5 else ''})")
        
        # Search in database (only among cast members)
        # Get top 5 matches to show debug info
        matches = self.db.search_similar(
            embedding,
            actor_ids=cast_actor_ids,
            threshold=similarity_threshold,
            limit=5,
            debug=debug
        )
        
        if matches:
            return matches[0]
        
        # If no match, show why - also check without actor filter to see if person exists
        if debug:
            print(f"    🔍 Checking entire database for best match...")
            # Check if there are ANY matches in the entire database
            all_matches = self.db.search_similar(
                embedding,
                actor_ids=None,  # Search all actors
                threshold=0.0,   # No threshold
                limit=5,
                debug=False
            )
            
            if all_matches:
                print(f"    📊 Top matches across ALL actors:")
                for i, m in enumerate(all_matches[:3], 1):
                    in_cast = "✓ IN CAST" if m['actor_id'] in cast_actor_ids else "✗ NOT IN CAST"
                    print(f"       {i}. {m['actor_name']}: {m['similarity']:.3f} ({m['confidence']}%) {in_cast}")
                
                best = all_matches[0]
                if best['similarity'] >= similarity_threshold:
                    if best['actor_id'] in cast_actor_ids:
                        print(f"    ⚠️  Match found but query returned 0 rows - possible database issue")
                    else:
                        print(f"    ⚠️  Best match is NOT in cast list:")
                        print(f"       {best['actor_name']}: {best['similarity']:.3f} ({best['confidence']}%)")
                else:
                    print(f"    ❌ No match above threshold {similarity_threshold}")
                    print(f"       Best match: {best['actor_name']} ({best['confidence']}%)")
                    print(f"       Try lowering threshold with --threshold parameter")
            else:
                print(f"    ❌ No embeddings found in entire database")
        
        return None
    
    def _process_objects(self, image_path: str, detections: List[Dict], 
                        category: str, output_path: Path, scene_context: Dict) -> List[Dict]:
        """Process detected objects with vision model analysis."""
        if not detections or not self.use_vision_analysis:
            return []
        
        print(f"\n📦 Processing {len(detections)} {category}...")
        
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
                print(f"  ✓ {detection['class']} {idx}")
        
        return results
    
    def process_image(self, image_path: str, movie_title: str,
                     output_dir: str = "output",
                     similarity_threshold: float = 0.6) -> Dict:
        """Process image with fast face recognition pipeline."""
        print(f"\n{'='*70}")
        print(f"🚀 UPDATED AGENTIC PIPELINE")
        print(f"📷 Image: {Path(image_path).name}")
        print(f"🎬 Movie: {movie_title}")
        print(f"{'='*70}\n")
        
        # Prepare cast data
        movie_context = self.prepare_movie_cast(movie_title)
        if not movie_context:
            print("❌ Failed to prepare cast data")
            return None
        
        cast_actor_ids = [member['id'] for member in movie_context['cast']]
        
        print(f"\n✓ Cast prepared: {len(cast_actor_ids)} actors")
        print(f"  Actor IDs: {cast_actor_ids}")
        
        # Detect all objects
        print(f"\n{'='*70}")
        print("🔍 ANALYZING IMAGE")
        print(f"{'='*70}\n")
        
        all_detections = self.detect_all_objects(image_path)
        
        if not all_detections['people']:
            print("⚠️  No people detected in image")
            # Continue anyway to detect other objects
        
        # Process each detected person
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        identified_people = []
        
        if all_detections['people']:
            print(f"\n👤 Identifying {len(all_detections['people'])} people...\n")
        
        for idx, detection in enumerate(all_detections['people'], 1):
            print(f"[{idx}/{len(all_detections['people'])}] Processing person...")
            
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
                print(f"  👁️  Analyzing details with vision model...")
                vision_details = self.analyze_person_details(str(crop_path))
            else:
                vision_details = {}
            
            if match:
                print(f"  ✓ Identified: {match['actor_name']} "
                      f"(confidence: {match['confidence']}%)")
                print(f"    Matched to: {Path(match['image_path']).name}")
                print(f"    Full path: {match['image_path']}")
                
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
                print(f"  ❌ Unknown person (no match above threshold)")
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
        print(f"\n🎬 Scene Analysis...")
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
        
        print(f"\n{'='*70}")
        print(f"✅ COMPLETE!")
        print(f"📄 Analysis: {result_file}")
        print(f"🖼️  Crops: {output_dir}/")
        print(f"{'='*70}\n")
        
        # Print summary
        print("📊 SUMMARY:")
        print(f"Movie: {movie_context['title']} ({movie_context['year']})")
        print(f"\nIdentified {len([p for p in identified_people if p['name']])} / "
              f"{len(identified_people)} people:")
        for person in identified_people:
            if person['name']:
                char = f" as {person['character']}" if person['character'] else ""
                print(f"  ✓ {person['name']}{char} ({person['confidence']}%)")
            else:
                print(f"  ❌ Unknown person")
        
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
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
