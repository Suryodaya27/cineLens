#!/usr/bin/env python3
"""
Advanced object detection supporting multiple models beyond YOLO.
Includes OWL-ViT for open-vocabulary detection (detects guitars, instruments, etc.)

This is a standalone tool - agentic_pipeline.py remains unchanged.
Use this when YOLO misses objects like guitars, instruments, accessories.
"""

import cv2
import torch
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import json


class AdvancedDetector:
    """Supports multiple detection models for better object detection."""
    
    def __init__(self, model_type: str = "yolo", model_name: str = None):
        """
        Initialize detector.
        
        Args:
            model_type: 'yolo', 'dino', 'grounding-dino', 'owl-vit', 'sam'
            model_name: Specific model name
        """
        self.model_type = model_type.lower()
        self.model_name = model_name
        self.model = None
        self.processor = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the appropriate detection model."""
        
        if self.model_type == "yolo":
            # YOLO - Fast, 80 classes
            from ultralytics import YOLO
            self.model_name = self.model_name or "yolov8x.pt"  # Use largest by default
            self.model = YOLO(self.model_name)
            print(f"✓ Loaded YOLO: {self.model_name}")
            
        elif self.model_type == "grounding-dino":
            # GroundingDINO - Text-prompted detection, detects ANYTHING
            try:
                from groundingdino.util.inference import load_model, predict
                self.model_name = self.model_name or "groundingdino_swint_ogc"
                # Note: Requires groundingdino installation
                print(f"✓ Loaded GroundingDINO: {self.model_name}")
                print("  Can detect ANY object with text prompts!")
            except ImportError:
                print("❌ GroundingDINO not installed")
                print("   Install: pip install groundingdino-py")
                raise
                
        elif self.model_type == "owl-vit":
            # OWL-ViT - Open-vocabulary detection
            try:
                from transformers import OwlViTProcessor, OwlViTForObjectDetection
                self.model_name = self.model_name or "google/owlvit-base-patch32"
                self.processor = OwlViTProcessor.from_pretrained(self.model_name)
                self.model = OwlViTForObjectDetection.from_pretrained(self.model_name)
                print(f"✓ Loaded OWL-ViT: {self.model_name}")
                print("  Can detect objects from text descriptions!")
            except ImportError:
                print("❌ Transformers not installed")
                print("   Install: pip install transformers")
                raise
                
        elif self.model_type == "dino":
            # DINO v2 - Better feature extraction
            try:
                from transformers import AutoImageProcessor, AutoModel
                self.model_name = self.model_name or "facebook/dinov2-large"
                self.processor = AutoImageProcessor.from_pretrained(self.model_name)
                self.model = AutoModel.from_pretrained(self.model_name)
                print(f"✓ Loaded DINO: {self.model_name}")
            except ImportError:
                print("❌ Transformers not installed")
                raise
                
        elif self.model_type == "sam":
            # Segment Anything Model - Segments everything
            try:
                from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
                self.model_name = self.model_name or "vit_h"
                # Note: Requires SAM checkpoint download
                print(f"✓ Loaded SAM: {self.model_name}")
                print("  Segments all objects in image!")
            except ImportError:
                print("❌ SAM not installed")
                print("   Install: pip install segment-anything")
                raise
        
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def detect_with_prompts(self, image_path: str, text_prompts: List[str],
                           confidence_threshold: float = 0.3) -> List[Dict]:
        """
        Detect objects using text prompts (works with OWL-ViT, GroundingDINO).
        
        Args:
            image_path: Path to image
            text_prompts: List of objects to detect (e.g., ["guitar", "microphone", "drum"])
            confidence_threshold: Minimum confidence
            
        Returns:
            List of detections with bboxes
        """
        if self.model_type == "owl-vit":
            return self._detect_owl_vit(image_path, text_prompts, confidence_threshold)
        elif self.model_type == "grounding-dino":
            return self._detect_grounding_dino(image_path, text_prompts, confidence_threshold)
        else:
            raise ValueError(f"{self.model_type} doesn't support text prompts")
    
    def _detect_owl_vit(self, image_path: str, text_prompts: List[str],
                       threshold: float) -> List[Dict]:
        """Detect using OWL-ViT."""
        from PIL import Image
        
        image = Image.open(image_path)
        inputs = self.processor(text=text_prompts, images=image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Process outputs
        target_sizes = torch.Tensor([image.size[::-1]])
        results = self.processor.post_process_object_detection(
            outputs=outputs, 
            target_sizes=target_sizes, 
            threshold=threshold
        )[0]
        
        detections = []
        for box, score, label in zip(results["boxes"], results["scores"], results["labels"]):
            if score >= threshold:
                x1, y1, x2, y2 = box.tolist()
                detections.append({
                    'class': text_prompts[label],
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': float(score)
                })
        
        return detections
    
    def _detect_grounding_dino(self, image_path: str, text_prompts: List[str],
                              threshold: float) -> List[Dict]:
        """Detect using GroundingDINO."""
        print("⚠️  GroundingDINO detection not yet implemented")
        print("   Use OWL-ViT instead: --model owl-vit")
        return []
    
    def detect_yolo(self, image_path: str, confidence_threshold: float = 0.5) -> List[Dict]:
        """Standard YOLO detection."""
        results = self.model(image_path)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                confidence = float(box.conf[0])
                
                if confidence >= confidence_threshold:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append({
                        'class': cls_name,
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': confidence
                    })
        
        return detections
    
    def detect(self, image_path: str, text_prompts: List[str] = None,
              confidence_threshold: float = 0.5) -> List[Dict]:
        """
        Universal detection method.
        
        Args:
            image_path: Path to image
            text_prompts: Optional text prompts for open-vocabulary models
            confidence_threshold: Minimum confidence
        """
        if self.model_type == "yolo":
            return self.detect_yolo(image_path, confidence_threshold)
        elif text_prompts and self.model_type in ["owl-vit", "grounding-dino"]:
            return self.detect_with_prompts(image_path, text_prompts, confidence_threshold)
        else:
            raise ValueError("Provide text_prompts for open-vocabulary models")


def compare_models(image_path: str):
    """Compare detection results from different models."""
    print(f"\n{'='*70}")
    print(f"Comparing Detection Models on: {Path(image_path).name}")
    print(f"{'='*70}\n")
    
    # Test YOLO
    print("1. YOLO (80 predefined classes)")
    print("-" * 70)
    try:
        yolo = AdvancedDetector("yolo", "yolov8x.pt")
        yolo_detections = yolo.detect(image_path)
        print(f"✓ Detected {len(yolo_detections)} objects")
        for det in yolo_detections[:5]:  # Show first 5
            print(f"  • {det['class']} (confidence: {det['confidence']:.2f})")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n2. OWL-ViT (Open-vocabulary, can detect anything)")
    print("-" * 70)
    try:
        # Define custom objects to detect
        custom_prompts = [
            "person", "guitar", "microphone", "drum", "piano",
            "bottle", "phone", "laptop", "bag", "watch",
            "sunglasses", "hat", "book", "pen", "cup"
        ]
        owl = AdvancedDetector("owl-vit")
        owl_detections = owl.detect(image_path, text_prompts=custom_prompts, confidence_threshold=0.2)
        print(f"✓ Detected {len(owl_detections)} objects")
        for det in owl_detections[:5]:
            print(f"  • {det['class']} (confidence: {det['confidence']:.2f})")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)


def save_detections(detections: List[Dict], output_file: str):
    """Save detections to JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(detections, f, indent=2)
    
    print(f"\n💾 Saved detections to: {output_file}")


def visualize_detections(image_path: str, detections: List[Dict], output_path: str = None):
    """Draw bounding boxes on image."""
    img = cv2.imread(image_path)
    
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        label = f"{det['class']} {det['confidence']:.2f}"
        
        # Draw box
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label
        cv2.putText(img, label, (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    if output_path:
        cv2.imwrite(output_path, img)
        print(f"🖼️  Saved visualization to: {output_path}")
    else:
        output_path = f"detections_{Path(image_path).name}"
        cv2.imwrite(output_path, img)
        print(f"🖼️  Saved visualization to: {output_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Advanced Object Detection - Detects objects YOLO misses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect guitars and instruments (OWL-ViT)
  python3 advanced_detector.py musician.jpg --model owl-vit \\
    --prompts person guitar microphone drum

  # Compare YOLO vs OWL-ViT
  python3 advanced_detector.py image.jpg --compare

  # Detect with visualization
  python3 advanced_detector.py image.jpg --model owl-vit \\
    --prompts person guitar bottle phone --visualize

  # Save results to JSON
  python3 advanced_detector.py image.jpg --model owl-vit \\
    --prompts guitar microphone --output results.json
        """
    )
    parser.add_argument("image", help="Input image")
    parser.add_argument("--model", default="owl-vit", 
                       choices=["yolo", "owl-vit", "grounding-dino"],
                       help="Detection model (default: owl-vit)")
    parser.add_argument("--prompts", nargs="+",
                       help="Text prompts for open-vocabulary models (e.g., guitar microphone bottle)")
    parser.add_argument("--compare", action="store_true",
                       help="Compare YOLO vs OWL-ViT")
    parser.add_argument("--visualize", action="store_true",
                       help="Save image with bounding boxes")
    parser.add_argument("--output", "-o",
                       help="Save detections to JSON file")
    parser.add_argument("--confidence", type=float, default=0.2,
                       help="Confidence threshold (default: 0.2)")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_models(args.image)
    else:
        # Default prompts if none provided
        if not args.prompts and args.model in ["owl-vit", "grounding-dino"]:
            args.prompts = [
                "person", "guitar", "microphone", "drum", "piano", "violin",
                "bottle", "cup", "phone", "laptop", "bag", "watch",
                "sunglasses", "hat", "book", "pen", "camera"
            ]
            print(f"ℹ️  Using default prompts: {', '.join(args.prompts[:10])}...")
        
        detector = AdvancedDetector(args.model)
        
        print(f"\n🔍 Detecting objects in: {Path(args.image).name}")
        print(f"   Model: {args.model}")
        print(f"   Confidence threshold: {args.confidence}")
        
        if args.prompts:
            detections = detector.detect(args.image, text_prompts=args.prompts, 
                                        confidence_threshold=args.confidence)
        else:
            detections = detector.detect(args.image, confidence_threshold=args.confidence)
        
        print(f"\n✅ Detected {len(detections)} objects:")
        
        # Group by class
        by_class = {}
        for det in detections:
            cls = det['class']
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(det)
        
        for cls, items in sorted(by_class.items()):
            print(f"\n  {cls.upper()}: {len(items)}")
            for i, det in enumerate(items, 1):
                print(f"    {i}. Confidence: {det['confidence']:.2f}")
        
        # Save to JSON if requested
        if args.output:
            save_detections(detections, args.output)
        
        # Visualize if requested
        if args.visualize:
            vis_output = f"detected_{Path(args.image).stem}.jpg"
            visualize_detections(args.image, detections, vis_output)
