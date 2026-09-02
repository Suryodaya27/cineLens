#!/usr/bin/env python3
"""
Agentic AI Pipeline: Intelligently detects all objects and uses specialized prompts for each.
"""

import cv2
import json
import argparse
import base64
from pathlib import Path
from typing import List, Dict, Tuple
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from .schema_validator import OutputNormalizer


class AgenticPipeline:
    def __init__(self, yolo_model: str = "yolov8n.pt", vision_model: str = "qwen3-vl:8b",
                 use_parallel: bool = False):
        """Initialize agentic pipeline with YOLO and vision model."""
        self.yolo = YOLO(yolo_model)
        self.vision_model = vision_model
        self.use_parallel = use_parallel
        self.print_lock = threading.Lock() if use_parallel else None
        
        import ollama
        self.ollama = ollama
        
        # Load prompts context
        prompts_file = Path(__file__).parent / "prompts_context.json"
        with open(prompts_file, 'r') as f:
            self.prompts = json.load(f)
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def detect_all_objects(self, image_path: str, min_confidence: float = 0.5) -> Dict:
        """Detect ALL objects in the image using YOLO."""
        print("🔍 Detecting all objects in image...")
        
        results = self.yolo(image_path)
        detections = {
            'people': [],
            'animals': [],
            'vehicles': [],
            'products': [],
            'electronics': [],
            'furniture': [],
            'other': []
        }
        
        # Category mappings
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
    
    def analyze_scene(self, image_path: str) -> Dict:
        """Analyze the overall scene."""
        print("\n🎬 Analyzing scene context...")
        
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
        
        return self._parse_json_response(response['message']['content'])
    
    def crop_and_save(self, image_path: str, bbox: Tuple, output_dir: str,
                     object_type: str, index: int, padding: float = 0.1) -> str:
        """Crop object from image and save."""
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
        
        # Crop
        cropped = img[y1:y2, x1:x2]
        
        # Save
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        input_name = Path(image_path).stem
        crop_filename = f"{input_name}_{object_type.replace(' ', '_')}_{index}.png"
        crop_path = output_path / crop_filename
        cv2.imwrite(str(crop_path), cropped)
        
        return str(crop_path)
    
    def analyze_object(self, crop_path: str, object_class: str, 
                      scene_context: Dict, identify_person: bool = True,
                      movie_context: Dict = None) -> Dict:
        """Analyze a single object using appropriate prompt."""
        image_data = self._encode_image(crop_path)
        
        # Get appropriate prompt
        if object_class == 'person':
            prompt_key = 'identify' if identify_person else 'describe'
            prompt = self.prompts['person'][prompt_key]['prompt']
        elif object_class in self.prompts:
            prompt = self.prompts[object_class]['prompt']
        else:
            prompt = self.prompts['default']['prompt'].format(object_type=object_class)
        
        # Add scene context to prompt
        context_info = f"\n\nScene context: {scene_context.get('setting', 'unknown setting')}, {scene_context.get('lighting', 'unknown lighting')}"
        
        # Add movie context if provided (for person identification)
        if movie_context and object_class == 'person' and identify_person:
            movie_info = f"\n\nIMPORTANT - Movie/Series Context:"
            if movie_context.get('title'):
                movie_info += f"\nThis image is from: {movie_context['title']}"
            if movie_context.get('cast'):
                movie_info += f"\nKnown cast members: {', '.join(movie_context['cast'])}"
            if movie_context.get('year'):
                movie_info += f"\nYear: {movie_context['year']}"
            movie_info += "\nPlease identify the person considering this context. They are likely one of the cast members."
            context_info += movie_info
        
        prompt += context_info
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        result = self._parse_json_response(response['message']['content'])
        result['object_class'] = object_class
        result['crop_image'] = crop_path
        
        return result
    
    def _parse_json_response(self, content: str) -> Dict:
        """Parse JSON from LLM response."""
        try:
            # Extract JSON if wrapped in markdown
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            return json.loads(content)
        except Exception as e:
            return {'raw_response': content, 'parse_error': str(e)}
    
    def process_category(self, image_path: str, detections: List[Dict],
                        category: str, output_dir: str, scene_context: Dict,
                        identify_person: bool = True, movie_context: Dict = None) -> List[Dict]:
        """Process all objects in a category."""
        if not detections:
            return []
        
        print(f"\n📦 Processing {len(detections)} {category}...")
        
        results = []
        
        # Crop all objects first
        crops = []
        for idx, detection in enumerate(detections, 1):
            crop_path = self.crop_and_save(
                image_path,
                detection['bbox'],
                output_dir,
                detection['class'],
                idx,
                padding=0.1
            )
            crops.append({
                'path': crop_path,
                'class': detection['class'],
                'confidence': detection['confidence'],
                'index': idx
            })
        
        # Analyze objects (parallel only if enabled AND multiple objects)
        if not self.use_parallel or len(crops) == 1:
            # Sequential processing
            for crop in crops:
                result = self.analyze_object(
                    crop['path'],
                    crop['class'],
                    scene_context,
                    identify_person,
                    movie_context
                )
                result['detection_confidence'] = crop['confidence']
                results.append(result)
                print(f"  ✅ {crop['class']} {crop['index']}")
        else:
            # Parallel processing (only when multiple objects)
            with ThreadPoolExecutor(max_workers=min(3, len(crops))) as executor:
                future_to_crop = {
                    executor.submit(
                        self.analyze_object,
                        crop['path'],
                        crop['class'],
                        scene_context,
                        identify_person,
                        movie_context
                    ): crop
                    for crop in crops
                }
                
                for future in as_completed(future_to_crop):
                    crop = future_to_crop[future]
                    try:
                        result = future.result()
                        result['detection_confidence'] = crop['confidence']
                        results.append(result)
                        print(f"  ✅ {crop['class']} {crop['index']}")
                    except Exception as e:
                        print(f"  ❌ Error: {crop['class']} {crop['index']}: {e}")
        
        return results
    
    def process_image(self, image_path: str, output_dir: str = "final-output",
                     identify_people: bool = True, movie_context: Dict = None) -> Dict:
        """Process complete image with agentic workflow."""
        print(f"\n{'='*70}")
        print(f"🤖 AGENTIC PIPELINE: {Path(image_path).name}")
        if movie_context:
            print(f"🎬 Movie Context: {movie_context.get('title', 'Unknown')}")
            if movie_context.get('cast'):
                print(f"   Cast: {', '.join(movie_context['cast'][:3])}{'...' if len(movie_context['cast']) > 3 else ''}")
        print(f"{'='*70}")
        
        # Step 1: Detect all objects
        detections = self.detect_all_objects(image_path)
        
        total_objects = sum(len(v) for v in detections.values())
        if total_objects == 0:
            print("\n❌ No objects detected")
            return None
        
        # Step 2: Analyze scene
        scene_context = self.analyze_scene(image_path)
        
        # Step 3: Process each category
        result = {
            'source_image': Path(image_path).name,
            'movie_context': movie_context if movie_context else None,
            'scene_analysis': scene_context,
            'detections_summary': {
                category: len(items) 
                for category, items in detections.items() 
                if items
            }
        }
        
        # Process each category
        if detections['people']:
            result['people'] = self.process_category(
                image_path, detections['people'], 'people',
                output_dir, scene_context, identify_people, movie_context
            )
        
        if detections['products']:
            result['products'] = self.process_category(
                image_path, detections['products'], 'products',
                output_dir, scene_context, True, None
            )
        
        if detections['animals']:
            result['animals'] = self.process_category(
                image_path, detections['animals'], 'animals',
                output_dir, scene_context, True, None
            )
        
        if detections['vehicles']:
            result['vehicles'] = self.process_category(
                image_path, detections['vehicles'], 'vehicles',
                output_dir, scene_context, True, None
            )
        
        if detections['electronics']:
            result['electronics'] = self.process_category(
                image_path, detections['electronics'], 'electronics',
                output_dir, scene_context, True, None
            )
        
        if detections['furniture']:
            result['furniture'] = self.process_category(
                image_path, detections['furniture'], 'furniture',
                output_dir, scene_context, True, None
            )
        
        if detections['other']:
            result['other_objects'] = self.process_category(
                image_path, detections['other'], 'other objects',
                output_dir, scene_context, True, None
            )
        
        # Normalize result to match fixed schema
        result = OutputNormalizer.normalize_output(result)
        
        # Save result
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        result_file = output_path / f"{Path(image_path).stem}_complete_analysis.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"✅ COMPLETE!")
        print(f"📄 Full analysis: {result_file}")
        print(f"🖼️  All crops: {output_dir}/")
        print(f"{'='*70}")
        
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Agentic AI Pipeline - Intelligently analyzes all objects"
    )
    parser.add_argument("image", help="Input image file")
    parser.add_argument("-o", "--output", default="final-output",
                       help="Output directory")
    parser.add_argument("--yolo-model", default="yolov8n.pt",
                       help="YOLO model")
    parser.add_argument("--vision-model", default="qwen3-vl:8b",
                       help="Ollama vision model")
    parser.add_argument("--parallel", action="store_true",
                       help="Use parallel processing (only useful for multiple objects)")
    parser.add_argument("--no-identify", action="store_true",
                       help="Don't identify people by name")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                       help="Minimum detection confidence")
    parser.add_argument("--movie", help="Movie/series title")
    parser.add_argument("--cast", nargs="+", help="Known cast members")
    parser.add_argument("--year", help="Movie/series year")
    parser.add_argument("--movie-json", help="Path to JSON file with movie context")
    
    args = parser.parse_args()
    
    # Build movie context if provided
    movie_context = None
    if args.movie or args.cast or args.year or args.movie_json:
        if args.movie_json:
            # Load from JSON file
            with open(args.movie_json, 'r') as f:
                movie_context = json.load(f)
        else:
            # Build from command line args
            movie_context = {}
            if args.movie:
                movie_context['title'] = args.movie
            if args.cast:
                movie_context['cast'] = args.cast
            if args.year:
                movie_context['year'] = args.year
    
    pipeline = AgenticPipeline(args.yolo_model, args.vision_model, args.parallel)
    
    result = pipeline.process_image(
        args.image,
        args.output,
        not args.no_identify,
        movie_context
    )
    
    if result:
        # Print summary
        print("\n📊 SUMMARY:")
        print(f"Scene: {result['scene_analysis'].get('setting', 'N/A')}")
        
        for category in ['people', 'products', 'animals', 'vehicles', 
                        'electronics', 'furniture', 'other_objects']:
            if category in result:
                print(f"\n{category.upper()}:")
                for item in result[category]:
                    if category == 'people':
                        name = item.get('name') or 'Unknown person'
                        print(f"  • {name}")
                        if item.get('held_items'):
                            print(f"    Holding: {item['held_items']}")
                    elif category == 'products':
                        brand = item.get('brand') or 'Unknown brand'
                        ptype = item.get('product_type', 'product')
                        print(f"  • {brand} {ptype}")
                    else:
                        obj_class = item.get('object_class', 'object')
                        print(f"  • {obj_class}")


if __name__ == "__main__":
    main()
