#!/usr/bin/env python3
"""
Quick test: detect all faces in an image and save crops.

Usage:
    python scripts/test_face_crops.py path/to/image.jpg
    python scripts/test_face_crops.py path/to/image.jpg --movie "Inception"
    python scripts/test_face_crops.py path/to/image.jpg --movie "Inception" --threshold 0.4

Output goes to test_crops/ folder.
"""

import sys
import os
import argparse
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from pipelines.updated_agentic_pipeline import UpdatedAgenticPipeline


def main():
    parser = argparse.ArgumentParser(description="Test face detection and cropping")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("--movie", default=None, help="Movie name (enables actor identification)")
    parser.add_argument("--threshold", type=float, default=0.4, help="Face similarity threshold")
    parser.add_argument("--output", default="test_crops", help="Output directory")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    print(f"📷 Image: {image_path}")
    print(f"📁 Output: {out_dir}/")
    print()

    # Init pipeline (no vision — just detection + face matching)
    pipeline = UpdatedAgenticPipeline(yolo_model="yolov8n.pt", use_vision_analysis=False)

    # Detect
    detections = pipeline.detect_all_objects(str(image_path))
    people = detections['people']
    print(f"\n👤 Detected {len(people)} people")

    if not people:
        print("No people detected.")
        pipeline.close()
        return

    # Optional: prepare cast for identification
    cast_actor_ids = []
    movie_context = None
    if args.movie:
        movie_context = pipeline.prepare_movie_cast(args.movie)
        if movie_context:
            cast_actor_ids = [m['id'] for m in movie_context['cast']]
            print(f"🎬 Movie: {movie_context['title']} ({movie_context['year']}) — {len(cast_actor_ids)} cast members")

    # Crop and identify each person
    print()
    for idx, detection in enumerate(people, 1):
        cropped = pipeline.crop_person(str(image_path), detection['bbox'])
        crop_path = out_dir / f"person_{idx}.png"
        cv2.imwrite(str(crop_path), cropped)

        label = f"Person {idx}"
        confidence = detection['confidence']

        if cast_actor_ids:
            match = pipeline.identify_person(cropped, cast_actor_ids, args.threshold)
            if match:
                label = f"{match['actor_name']} ({match['confidence']}%)"
                # Save with actor name
                safe_name = match['actor_name'].replace(' ', '_')
                named_path = out_dir / f"person_{idx}_{safe_name}.png"
                cv2.imwrite(str(named_path), cropped)

        print(f"  [{idx}] {label}  (detection: {confidence:.0%})  → {crop_path}")

    pipeline.close()

    total_objects = sum(len(v) for v in detections.values())
    print(f"\n✅ Done — {len(people)} face crops saved to {out_dir}/")
    print(f"   Total objects detected: {total_objects}")
    for cat, items in detections.items():
        if items and cat != 'people':
            print(f"   {cat}: {len(items)}")


if __name__ == '__main__':
    main()
