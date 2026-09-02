#!/usr/bin/env python3
"""
Complete pipeline: Crop objects + Classify with Vision LLM
"""

import argparse
from pathlib import Path
from .crop_pipeline import AutoCropPipeline
from .vision_classifier import VisionClassifier
import json


def main():
    parser = argparse.ArgumentParser(
        description="Crop and classify objects with AI"
    )
    parser.add_argument("input", help="Input image or directory")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    
    # Cropping options
    parser.add_argument("-c", "--classes", nargs="+", default=["person"],
                       help="Target classes to detect")
    parser.add_argument("--crop-model", default="yolov8n.pt",
                       help="YOLO model for detection")
    parser.add_argument("-p", "--padding", type=float, default=0.1,
                       help="Padding around crops")
    parser.add_argument("--aspect-ratio", help="Target aspect ratio (e.g., 1:1)")
    parser.add_argument("--remove-bg", action="store_true",
                       help="Remove background")
    
    # Vision classification options
    parser.add_argument("--classify", action="store_true",
                       help="Classify cropped objects with vision LLM")
    parser.add_argument("--vision-provider", default="ollama",
                       choices=["openai", "anthropic", "google", "ollama"],
                       help="Vision model provider")
    parser.add_argument("--vision-model", help="Specific vision model")
    parser.add_argument("--detail", default="standard",
                       choices=["basic", "standard", "detailed"],
                       help="Classification detail level")
    parser.add_argument("--identify", action="store_true",
                       help="Attempt to identify people by name (use with caution)")
    
    args = parser.parse_args()
    
    # Step 1: Crop objects
    print("Step 1: Detecting and cropping objects...")
    crop_pipeline = AutoCropPipeline(args.crop_model, args.remove_bg)
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        cropped_files = crop_pipeline.process_image(
            args.input,
            args.output,
            args.classes,
            args.padding,
            0.5,
            args.remove_bg,
            args.aspect_ratio
        )
    else:
        results = crop_pipeline.process_batch(
            args.input,
            args.output,
            args.classes,
            args.padding,
            0.5,
            args.remove_bg,
            args.aspect_ratio
        )
        cropped_files = [f for files in results.values() for f in files]
    
    if not cropped_files:
        print("No objects detected!")
        return
    
    print(f"\n✓ Cropped {len(cropped_files)} objects")
    
    # Step 2: Classify with vision LLM (optional)
    if args.classify:
        print("\nStep 2: Classifying objects with vision LLM...")
        classifier = VisionClassifier(args.vision_provider, args.vision_model)
        
        # Extract object types from filenames
        object_types = []
        for f in cropped_files:
            # Extract class from filename (e.g., "image_person_1.png" -> "person")
            parts = Path(f).stem.split('_')
            obj_type = parts[-2] if len(parts) >= 2 else "object"
            object_types.append(obj_type)
        
        classifications = classifier.batch_classify(
            cropped_files,
            object_types,
            args.detail,
            args.identify
        )
        
        # Print results
        print("\n" + "="*60)
        print("CLASSIFICATION RESULTS")
        print("="*60)
        
        for result in classifications:
            if 'error' not in result:
                print(f"\n📸 {Path(result['image_path']).name}")
                print(f"   {result['description']}")
        
        # Save to JSON
        results_file = Path(args.output) / "classifications.json"
        with open(results_file, 'w') as f:
            json.dump(classifications, f, indent=2)
        
        print(f"\n✓ Classifications saved to {results_file}")


if __name__ == "__main__":
    main()
