#!/usr/bin/env python3
"""
Smart AI pipeline: Analyzes original image for context, then crops and identifies individuals.
"""

import cv2
import json
import argparse
from pathlib import Path
from typing import List, Dict
from ultralytics import YOLO
import base64


class SmartPipeline:
    def __init__(self, yolo_model: str = "yolov8x.pt", vision_model: str = "qwen3-vl:8b"):
        """Initialize with YOLO for detection and Ollama for vision."""
        self.yolo = YOLO(yolo_model)
        self.vision_model = vision_model
        
        import ollama
        self.ollama = ollama
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def analyze_scene(self, image_path: str) -> Dict:
        """Analyze the full image for background and products context."""
        print("🔍 Analyzing scene context...")
        
        image_data = self._encode_image(image_path)
        
        prompt = """Analyze this image and provide a JSON response with:
1. background: Describe the setting/location/environment
2. products: List any visible products, brands, or objects (exclude people)
3. scene_type: Type of scene (indoor/outdoor, event type, etc.)

Format as valid JSON only, no other text."""
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        try:
            # Try to parse JSON from response
            content = response['message']['content']
            # Extract JSON if wrapped in markdown
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            scene_data = json.loads(content)
            return scene_data
        except:
            # Fallback if JSON parsing fails
            return {
                "background": response['message']['content'],
                "products": [],
                "scene_type": "unknown"
            }
    
    def detect_and_crop_people(self, image_path: str, output_dir: str, 
                               padding: float = 0.1, aspect_ratio: str = None) -> List[Dict]:
        """Detect people and create crops."""
        print("👤 Detecting people...")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        img = cv2.imread(image_path)
        results = self.yolo(image_path)
        
        crops = []
        person_count = 0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                
                if cls_name == 'person':
                    person_count += 1
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    
                    if confidence < 0.5:
                        continue
                    
                    # Add padding
                    bbox = self._add_padding(
                        (int(x1), int(y1), int(x2), int(y2)),
                        img.shape,
                        padding,
                        aspect_ratio
                    )
                    
                    # Crop
                    x1, y1, x2, y2 = bbox
                    cropped = img[y1:y2, x1:x2]
                    
                    # Save crop
                    input_name = Path(image_path).stem
                    crop_filename = f"{input_name}_person_{person_count}.png"
                    crop_path = output_path / crop_filename
                    cv2.imwrite(str(crop_path), cropped)
                    
                    crops.append({
                        'path': str(crop_path),
                        'bbox': bbox,
                        'confidence': confidence,
                        'person_id': person_count
                    })
        
        print(f"✓ Found {len(crops)} people")
        return crops
    
    def _add_padding(self, bbox, img_shape, padding, aspect_ratio):
        """Add padding and apply aspect ratio."""
        x1, y1, x2, y2 = bbox
        h, w = img_shape[:2]
        
        width = x2 - x1
        height = y2 - y1
        
        pad_x = int(width * padding)
        pad_y = int(height * padding)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        if aspect_ratio:
            x1, y1, x2, y2 = self._apply_aspect_ratio(
                (x1, y1, x2, y2), img_shape, aspect_ratio
            )
        
        return (x1, y1, x2, y2)
    
    def _apply_aspect_ratio(self, bbox, img_shape, aspect_ratio):
        """Apply aspect ratio to bbox."""
        x1, y1, x2, y2 = bbox
        h, w = img_shape[:2]
        
        try:
            ratio_w, ratio_h = map(float, aspect_ratio.split(':'))
            target_ratio = ratio_w / ratio_h
        except:
            return bbox
        
        current_width = x2 - x1
        current_height = y2 - y1
        current_ratio = current_width / current_height
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        if current_ratio > target_ratio:
            new_height = current_width / target_ratio
            new_width = current_width
        else:
            new_width = current_height * target_ratio
            new_height = current_height
        
        x1 = int(center_x - new_width / 2)
        x2 = int(center_x + new_width / 2)
        y1 = int(center_y - new_height / 2)
        y2 = int(center_y + new_height / 2)
        
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        return (x1, y1, x2, y2)
    
    def identify_person(self, crop_path: str, person_id: int, 
                       scene_context: Dict, identify_name: bool = True) -> Dict:
        """Identify a single person with context."""
        print(f"  Analyzing person {person_id}...")
        
        image_data = self._encode_image(crop_path)
        
        if identify_name:
            prompt = f"""Analyze this person and provide a JSON response with:
1. actor_name: Full name if you recognize them with 100% certainty (or null if unsure)
2. actor_description: Detailed description of face, hair, facial features
3. clothing: Description of what they're wearing
4. pose: Their body position and pose
5. confidence: Your confidence level in identification (0-100)

Context: This person is in a {scene_context.get('scene_type', 'scene')} with background: {scene_context.get('background', 'unknown')}

Format as valid JSON only, no other text."""
        else:
            prompt = f"""Describe this person and provide a JSON response with:
1. actor_description: Detailed description of face, hair, facial features
2. clothing: Description of what they're wearing
3. pose: Their body position and pose

Context: This person is in a {scene_context.get('scene_type', 'scene')} with background: {scene_context.get('background', 'unknown')}

Format as valid JSON only, no other text."""
        
        response = self.ollama.chat(
            model=self.vision_model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        try:
            content = response['message']['content']
            # Extract JSON if wrapped
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            person_data = json.loads(content)
            
            # Only include actor_name if confidence is 100 or very high
            if identify_name and 'actor_name' in person_data:
                confidence = person_data.get('confidence', 0)
                if confidence < 90 or person_data['actor_name'] in ['unknown', 'Unknown', None, 'null']:
                    person_data['actor_name'] = None
            
            return person_data
        except Exception as e:
            print(f"    ⚠️  JSON parse error: {e}")
            return {
                "actor_name": None if identify_name else None,
                "actor_description": response['message']['content'],
                "clothing": "Unable to parse",
                "pose": "Unable to parse"
            }
    
    def process_image(self, image_path: str, output_dir: str = "final-output",
                     identify_names: bool = True, padding: float = 0.1,
                     aspect_ratio: str = None) -> Dict:
        """Process a single image completely."""
        print(f"\n{'='*60}")
        print(f"Processing: {Path(image_path).name}")
        print(f"{'='*60}\n")
        
        # Step 1: Analyze scene
        scene_context = self.analyze_scene(image_path)
        
        # Step 2: Detect and crop people
        crops = self.detect_and_crop_people(image_path, output_dir, padding, aspect_ratio)
        
        if not crops:
            print("❌ No people detected")
            return None
        
        # Step 3: Identify each person
        print(f"\n🎭 Identifying {len(crops)} people...")
        people_data = []
        
        for crop in crops:
            person_data = self.identify_person(
                crop['path'],
                crop['person_id'],
                scene_context,
                identify_names
            )
            person_data['crop_image'] = crop['path']
            person_data['detection_confidence'] = crop['confidence']
            people_data.append(person_data)
        
        # Step 4: Build final result
        result = {
            "source_image": str(Path(image_path).name),
            "background_info": scene_context.get('background', ''),
            "scene_type": scene_context.get('scene_type', ''),
            "products": scene_context.get('products', []),
            "people": people_data
        }
        
        # Step 5: Save result
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        result_file = output_path / f"{Path(image_path).stem}_analysis.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Analysis complete!")
        print(f"📄 Results saved to: {result_file}")
        print(f"🖼️  Crops saved to: {output_dir}/")
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Smart AI image analysis pipeline")
    parser.add_argument("image", help="Input image file")
    parser.add_argument("-o", "--output", default="final-output", 
                       help="Output directory (default: final-output)")
    parser.add_argument("--yolo-model", default="yolov8x.pt",
                       help="YOLO model for detection")
    parser.add_argument("--vision-model", default="qwen3-vl:8b",
                       help="Ollama vision model")
    parser.add_argument("--no-identify", action="store_true",
                       help="Don't attempt to identify people by name")
    parser.add_argument("-p", "--padding", type=float, default=0.1,
                       help="Padding around crops (0.0-1.0)")
    parser.add_argument("--aspect-ratio", help="Target aspect ratio (e.g., 1:1, 16:9)")
    
    args = parser.parse_args()
    
    pipeline = SmartPipeline(args.yolo_model, args.vision_model)
    
    result = pipeline.process_image(
        args.image,
        args.output,
        not args.no_identify,
        args.padding,
        args.aspect_ratio
    )
    
    if result:
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Scene: {result['scene_type']}")
        print(f"Background: {result['background_info']}")
        if result['products']:
            print(f"Products: {', '.join(result['products']) if isinstance(result['products'], list) else result['products']}")
        print(f"\nPeople detected: {len(result['people'])}")
        for i, person in enumerate(result['people'], 1):
            name = person.get('actor_name')
            if name:
                print(f"  {i}. {name}")
            else:
                print(f"  {i}. {person.get('actor_description', 'Unknown')[:50]}...")


if __name__ == "__main__":
    main()
