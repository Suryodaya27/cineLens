#!/usr/bin/env python3
"""
Pipeline worker — pulls jobs from Redis, runs ML pipeline, publishes progress.

Usage:
    python worker.py
"""

import json
import os
import time
import cv2
import redis
import traceback
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from pipelines.updated_agentic_pipeline import UpdatedAgenticPipeline
from logging_config import get_logger, JobContext

logger = get_logger("worker")

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')
DEFAULT_VISION_MODEL = os.getenv('VISION_MODEL', 'qwen3.8:latest')
TEMP_DIR = Path("temp_api_uploads")
TEMP_DIR.mkdir(exist_ok=True)

JOB_QUEUE = 'cinelens:jobs'
JOB_TTL = 3600  # results expire after 1 hour


def get_redis():
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish(r: redis.Redis, job_id: str, event: str, data: dict):
    """Publish a progress event and store it in the job's event list."""
    data.setdefault("job_id", job_id)
    msg = json.dumps({"event": event, "data": data})
    r.publish(f"job:{job_id}", msg)
    r.rpush(f"job:{job_id}:events", msg)
    r.expire(f"job:{job_id}:events", JOB_TTL)


def download_image(url: str, save_path: Path) -> bool:
    """Download image from URL."""
    import requests
    try:
        # ponytail: verify=False because corporate Cisco Umbrella proxy re-signs certs.
        # Proper fix: add Umbrella root CA to the image. This is a hackathon workaround.
        resp = requests.get(str(url), timeout=30, stream=True, verify=False)
        resp.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.error("Image download failed", extra={"error": str(e), "image_url": str(url)})
        return False


def upload_to_imgbb(image_path: str, api_key: str) -> Optional[str]:
    """Upload a single image to ImgBB, return hosted URL."""
    import requests, base64
    try:
        with open(image_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        resp = requests.post(
            'https://api.imgbb.com/1/upload',
            data={'key': api_key, 'image': b64},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()['data']['url']
    except Exception as e:
        logger.warning("ImgBB upload failed", extra={"error": str(e), "detail": image_path})
        return None


def _reclassify_objects(result: dict) -> dict:
    """
    Move misclassified objects to the correct category.
    
    YOLO only knows 80 COCO classes so it often gets the category wrong
    (e.g. armor suit → vehicle). The vision model's description is more
    accurate. Check each object and move it if the description clearly
    doesn't belong in YOLO's category.
    """
    # Keywords that indicate an object actually belongs to a category
    category_keywords = {
        'vehicles': {'car', 'truck', 'bus', 'motorcycle', 'bicycle', 'boat',
                      'airplane', 'train', 'van', 'suv', 'sedan', 'vehicle'},
        'electronics': {'phone', 'laptop', 'computer', 'tablet', 'monitor',
                         'keyboard', 'mouse', 'remote', 'tv', 'television',
                         'camera', 'speaker', 'headphone', 'electronic'},
        'furniture': {'chair', 'table', 'couch', 'sofa', 'bed', 'desk',
                       'shelf', 'cabinet', 'stool', 'bench', 'furniture'},
        'animals': {'dog', 'cat', 'bird', 'horse', 'cow', 'sheep', 'fish',
                     'animal', 'pet', 'wildlife'},
        'products': {'bottle', 'cup', 'glass', 'food', 'drink', 'container'},
    }

    for cat in ['vehicles', 'electronics', 'furniture', 'animals', 'products']:
        kept = []
        for obj in result.get(cat, []):
            # Get the vision model's description of what this actually is
            obj_type = str(obj.get('type', obj.get('product_type', obj.get('breed', '')))).lower()
            obj_desc = str(obj.get('distinctive_features', '')).lower()
            combined = f"{obj_type} {obj_desc}"

            # Check if any keyword for this category appears in the description
            keywords = category_keywords.get(cat, set())
            belongs = any(kw in combined for kw in keywords)

            if belongs:
                kept.append(obj)
            else:
                # Move to other_objects
                result['other_objects'].append(obj)
        result[cat] = kept

    # Update detection summary counts
    result['detections_summary'] = {
        'people': len(result.get('people', [])),
        'products': len(result.get('products', [])),
        'animals': len(result.get('animals', [])),
        'vehicles': len(result.get('vehicles', [])),
        'electronics': len(result.get('electronics', [])),
        'furniture': len(result.get('furniture', [])),
        'other_objects': len(result.get('other_objects', []))
    }

    return result


def process_job(r: redis.Redis, job_id: str, params: dict, cache_key: str = None):
    """Run the full analysis pipeline for one job."""
    start_time = datetime.now()
    request_id = job_id
    temp_request_dir = TEMP_DIR / request_id
    temp_input_dir = temp_request_dir / "input"
    temp_output_dir = temp_request_dir / "output"
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    with JobContext(job_id):
        try:
            image_url = params['image_url']
            movie_name = params['movie_name']
            enable_vision = params.get('enable_vision', 0)
            similarity_threshold = params.get('similarity_threshold', 0.6)
            vision_model = params.get('vision_model') or DEFAULT_VISION_MODEL

            logger.info("Job started", extra={"step": "start", "movie": movie_name, "image_url": image_url})

            # Step 1: Download
            publish(r, job_id, "progress", {"step": "download", "message": "Downloading image..."})
            logger.info("Downloading image", extra={"step": "download", "image_url": image_url})
            image_path = temp_input_dir / f"input_{request_id}.jpg"
            if not download_image(image_url, image_path):
                logger.error("Image download failed", extra={"step": "download", "image_url": image_url})
                publish(r, job_id, "error", {"message": "Failed to download image"})
                r.hset(f"job:{job_id}", "status", "error")
                return
            logger.info("Image downloaded", extra={"step": "download"})
            publish(r, job_id, "progress", {"step": "download", "message": "Image downloaded", "done": True})

            # Step 2: Init pipeline
            publish(r, job_id, "progress", {"step": "init", "message": "Initializing AI pipeline..."})
            logger.info("Initializing pipeline", extra={"step": "init", "detail": vision_model})
            pipeline = UpdatedAgenticPipeline(
                yolo_model="yolov8n.pt",
                vision_model=vision_model,
                use_vision_analysis=bool(enable_vision)
            )
            logger.info("Pipeline ready", extra={"step": "init"})
            publish(r, job_id, "progress", {"step": "init", "message": "Pipeline ready", "done": True})

            # Start scene analysis in background (runs on Ollama while steps 3-5 use CPU/network)
            scene_result = {}
            scene_thread = None
            if pipeline.use_vision_analysis:
                def _run_scene():
                    scene_result['data'] = pipeline.analyze_scene_with_vision(str(image_path))
                scene_thread = threading.Thread(target=_run_scene, daemon=True)
                scene_thread.start()
                logger.info("Scene analysis started in background", extra={"step": "scene"})

            # Step 3: Cast (runs while Ollama is busy with scene analysis)
            publish(r, job_id, "progress", {"step": "cast", "message": f'Looking up cast for "{movie_name}"...'})
            logger.info("Looking up cast", extra={"step": "cast", "movie": movie_name})
            movie_context = pipeline.prepare_movie_cast(movie_name)
            if not movie_context:
                logger.error("Movie not found in TMDB", extra={"step": "cast", "movie": movie_name})
                publish(r, job_id, "error", {"message": f"Could not find movie: {movie_name}"})
                pipeline.close()
                r.hset(f"job:{job_id}", "status", "error")
                return
            cast_actor_ids = [m['id'] for m in movie_context['cast']]
            logger.info("Cast loaded", extra={"step": "cast", "count": len(cast_actor_ids), "movie": movie_context['title']})
            publish(r, job_id, "progress", {
                "step": "cast",
                "message": f"Found {len(cast_actor_ids)} cast members for {movie_context['title']} ({movie_context['year']})",
                "done": True
            })

            # Step 4: Detect
            publish(r, job_id, "progress", {"step": "detect", "message": "Detecting objects with YOLO..."})
            logger.info("Running YOLO detection", extra={"step": "detect"})
            all_detections = pipeline.detect_all_objects(str(image_path))
            total = sum(len(v) for v in all_detections.values())
            people_count = len(all_detections['people'])
            logger.info("Detection complete", extra={"step": "detect", "count": total, "detail": f"{people_count} people"})
            publish(r, job_id, "progress", {
                "step": "detect",
                "message": f"Detected {total} objects ({people_count} people)",
                "done": True
            })

            # Step 5: Identify people
            output_path = Path(str(temp_output_dir))
            identified_people = []

            for idx, detection in enumerate(all_detections['people'], 1):
                publish(r, job_id, "progress", {"step": "identify", "message": f"Identifying person {idx}/{people_count}..."})
                logger.info("Identifying person", extra={"step": "identify", "detail": f"{idx}/{people_count}"})

                cropped = pipeline.crop_person(str(image_path), detection['bbox'])
                input_name = Path(str(image_path)).stem
                crop_filename = f"{input_name}_person_{idx}.png"
                crop_path = output_path / crop_filename
                cv2.imwrite(str(crop_path), cropped)

                match = pipeline.identify_person(cropped, cast_actor_ids, similarity_threshold)

                vision_details = {}
                if pipeline.use_vision_analysis:
                    publish(r, job_id, "progress", {"step": "identify", "message": f"Analyzing person {idx}/{people_count} with vision model..."})
                    vision_details = pipeline.analyze_person_details(str(crop_path))

                if match:
                    cast_member = next((m for m in movie_context['cast'] if m['id'] == match['actor_id']), None)
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
                            'description': 'Not analyzed', 'colors': [],
                            'style': 'Not analyzed', 'accessories': []
                        }),
                        'pose': vision_details.get('pose', 'Not analyzed'),
                        'expression': vision_details.get('expression', 'Not analyzed'),
                        'held_items': vision_details.get('held_items', []),
                        'object_class': 'person',
                        'crop_image': str(crop_path),
                        'detection_confidence': detection['confidence']
                    }
                    logger.info("Person identified", extra={"step": "identify", "actor": match['actor_name'], "detail": f"{match['confidence']}%"})
                    publish(r, job_id, "progress", {
                        "step": "identify",
                        "message": f"Identified: {match['actor_name']} ({match['confidence']}%)",
                        "done": True
                    })
                else:
                    person_data = {
                        'name': None, 'profession': None, 'character': None,
                        'confidence': 0, 'gender': 'unknown',
                        'facial_features': 'Face detected but not identified',
                        'clothing': {'description': 'Not analyzed', 'colors': [],
                                     'style': 'Not analyzed', 'accessories': []},
                        'pose': 'Not analyzed', 'expression': 'Not analyzed',
                        'held_items': [], 'object_class': 'person',
                        'crop_image': str(crop_path),
                        'detection_confidence': detection['confidence']
                    }
                    logger.info("Person not matched", extra={"step": "identify", "detail": f"person {idx} below threshold"})
                    publish(r, job_id, "progress", {
                        "step": "identify",
                        "message": f"Person {idx}: unknown (no match above threshold)",
                        "done": True
                    })
                identified_people.append(person_data)

            # Step 6: Scene analysis — wait for background thread to finish
            publish(r, job_id, "progress", {"step": "scene", "message": "Analyzing scene..."})
            logger.info("Waiting for scene analysis", extra={"step": "scene"})
            if scene_thread:
                scene_thread.join()  # wait for Ollama to finish (may already be done)
            scene_analysis = scene_result.get('data', {})
            logger.info("Scene analysis complete", extra={"step": "scene"})
            publish(r, job_id, "progress", {"step": "scene", "message": "Scene analysis complete", "done": True})

            # Step 7: Other objects
            result = {
                'source_image': Path(str(image_path)).name,
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
                'products': [], 'animals': [], 'vehicles': [],
                'electronics': [], 'furniture': [], 'other_objects': []
            }

            if pipeline.use_vision_analysis:
                for det_key, cat_key in [('products', 'products'), ('animals', 'animal'),
                                          ('vehicles', 'vehicle'), ('electronics', 'electronics'),
                                          ('furniture', 'furniture'), ('other', 'default')]:
                    items = all_detections[det_key]
                    if items:
                        logger.info("Analyzing objects", extra={"step": "objects", "detail": f"{len(items)} {det_key}"})
                        publish(r, job_id, "progress", {"step": "objects", "message": f"Analyzing {len(items)} {det_key}..."})
                        out_key = 'other_objects' if det_key == 'other' else det_key
                        result[out_key] = pipeline._process_objects(
                            str(image_path), items, cat_key, output_path, scene_analysis
                        )

                # Reclassify objects if vision model disagrees with YOLO's category
                result = _reclassify_objects(result)

            pipeline.close()

            # Step 8: Upload crops
            publish(r, job_id, "progress", {"step": "upload", "message": "Uploading cropped images..."})
            logger.info("Uploading crops to ImgBB", extra={"step": "upload"})
            if IMGBB_API_KEY:
                # Upload person crops
                for person in result['people']:
                    local_path = person.get('crop_image', '')
                    if local_path and Path(local_path).exists():
                        url = upload_to_imgbb(local_path, IMGBB_API_KEY)
                        if url:
                            person['crop_image'] = url
                            person['crop_image_hosted'] = True
                # Upload object crops
                for key in ['products', 'animals', 'vehicles', 'electronics', 'furniture', 'other_objects']:
                    for obj in result.get(key, []):
                        local_path = obj.get('crop_image', '')
                        if local_path and Path(local_path).exists():
                            url = upload_to_imgbb(local_path, IMGBB_API_KEY)
                            if url:
                                obj['crop_image'] = url
                                obj['crop_image_hosted'] = True

            logger.info("Uploads complete", extra={"step": "upload"})
            publish(r, job_id, "progress", {"step": "upload", "message": "Uploads complete", "done": True})

            processing_time = (datetime.now() - start_time).total_seconds()

            # Done — store result and publish complete
            final = {
                "success": True,
                "message": "Image analyzed successfully",
                "job_id": job_id,
                "data": result,
                "processing_time": processing_time
            }
            r.hset(f"job:{job_id}", "status", "complete")
            r.hset(f"job:{job_id}", "result", json.dumps(final))
            r.expire(f"job:{job_id}", JOB_TTL)

            # Cache result for future identical requests (24h)
            if cache_key:
                r.set(cache_key, json.dumps(final), ex=86400)

            publish(r, job_id, "complete", final)

            logger.info("Job completed", extra={"step": "done", "duration": f"{processing_time:.1f}s"})

        except Exception as e:
            logger.exception("Job failed", extra={"error": str(e)})
            publish(r, job_id, "error", {"message": str(e)})
            r.hset(f"job:{job_id}", "status", "error")

        finally:
            # Cleanup temp files
            import shutil
            if temp_request_dir.exists():
                shutil.rmtree(temp_request_dir, ignore_errors=True)


def main():
    r = get_redis()
    logger.info("Worker started", extra={"detail": f"queue={JOB_QUEUE} redis={REDIS_URL} vision={DEFAULT_VISION_MODEL}"})

    while True:
        try:
            # BLPOP blocks until a job is available
            result = r.blpop(JOB_QUEUE, timeout=1)
            if result is None:
                continue

            _, raw = result
            job = json.loads(raw)
            job_id = job['job_id']
            params = job['params']
            cache_key = job.get('cache_key')

            logger.info("Job received", extra={
                "request_id": job_id,
                "movie": params.get('movie_name'),
                "detail": f"vision={'enabled' if params.get('enable_vision') else 'disabled'}"
            })

            r.hset(f"job:{job_id}", "status", "processing")
            process_job(r, job_id, params, cache_key)

        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            logger.warning("Redis connection lost, reconnecting in 2s")
            time.sleep(2)
            try:
                r = get_redis()
            except Exception:
                pass
        except Exception as e:
            logger.exception("Failed to process job", extra={"error": str(e)})


if __name__ == '__main__':
    main()
