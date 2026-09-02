#!/usr/bin/env python3
"""
AI-powered image cropping pipeline for actors and products.
Uses YOLO for detection and optional background removal.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from ultralytics import YOLO
from PIL import Image
import argparse


class AutoCropPipeline:
    def __init__(self, model_name: str = "yolov8x.pt", use_bg_removal: bool = False):
        """
        Initialize the cropping pipeline.
        
        Args:
            model_name: YOLO model to use (yolov8n.pt, yolov8s.pt, etc.)
            use_bg_removal: Whether to use background removal
        """
        self.model = YOLO(model_name)
        self.use_bg_removal = use_bg_removal
        
        if use_bg_removal:
            from rembg import remove
            self.remove_bg = remove
    
    def detect_subjects(self, image_path: str, target_classes: List[str] = None) -> List[dict]:
        """
        Detect people or products in the image.
        
        Args:
            image_path: Path to input image
            target_classes: List of class names to detect (e.g., ['person', 'bottle'])
        
        Returns:
            List of detection dictionaries with bbox and confidence
        """
        if target_classes is None:
            target_classes = ['person']  # Default to detecting people
        
        results = self.model(image_path)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                
                if cls_name in target_classes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    
                    detections.append({
                        'class': cls_name,
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': confidence
                    })
        
        return detections
    
    def add_padding(self, bbox: Tuple[int, int, int, int], 
                    img_shape: Tuple[int, int], 
                    padding_percent: float = 0.1,
                    aspect_ratio: Optional[str] = None) -> Tuple[int, int, int, int]:
        """
        Add padding around bounding box and optionally enforce aspect ratio.
        
        Args:
            bbox: Original bounding box (x1, y1, x2, y2)
            img_shape: Image shape (height, width)
            padding_percent: Padding to add
            aspect_ratio: Target aspect ratio (e.g., '1:1', '16:9', '4:3', '9:16')
        """
        x1, y1, x2, y2 = bbox
        h, w = img_shape[:2]
        
        width = x2 - x1
        height = y2 - y1
        
        pad_x = int(width * padding_percent)
        pad_y = int(height * padding_percent)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        # Apply aspect ratio if specified
        if aspect_ratio:
            x1, y1, x2, y2 = self._apply_aspect_ratio(
                (x1, y1, x2, y2), img_shape, aspect_ratio
            )
        
        return (x1, y1, x2, y2)
    
    def _apply_aspect_ratio(self, bbox: Tuple[int, int, int, int],
                           img_shape: Tuple[int, int],
                           aspect_ratio: str) -> Tuple[int, int, int, int]:
        """Adjust bounding box to match target aspect ratio."""
        x1, y1, x2, y2 = bbox
        h, w = img_shape[:2]
        
        # Parse aspect ratio
        try:
            ratio_w, ratio_h = map(float, aspect_ratio.split(':'))
            target_ratio = ratio_w / ratio_h
        except:
            print(f"Warning: Invalid aspect ratio '{aspect_ratio}', ignoring")
            return bbox
        
        current_width = x2 - x1
        current_height = y2 - y1
        current_ratio = current_width / current_height
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        if current_ratio > target_ratio:
            # Current box is wider, adjust height
            new_height = current_width / target_ratio
            new_width = current_width
        else:
            # Current box is taller, adjust width
            new_width = current_height * target_ratio
            new_height = current_height
        
        # Calculate new coordinates centered on the original box
        x1 = int(center_x - new_width / 2)
        x2 = int(center_x + new_width / 2)
        y1 = int(center_y - new_height / 2)
        y2 = int(center_y + new_height / 2)
        
        # Ensure within image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        return (x1, y1, x2, y2)
    
    def crop_image(self, image_path: str, bbox: Tuple[int, int, int, int], 
                   remove_bg: bool = False) -> np.ndarray:
        """Crop image to bounding box with optional background removal."""
        img = cv2.imread(image_path)
        x1, y1, x2, y2 = bbox
        cropped = img[y1:y2, x1:x2]
        
        if remove_bg and self.use_bg_removal:
            # Convert to PIL for rembg
            pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
            pil_img = self.remove_bg(pil_img)
            cropped = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        
        return cropped
    
    def process_image(self, 
                     input_path: str, 
                     output_dir: str,
                     target_classes: List[str] = None,
                     padding: float = 0.1,
                     min_confidence: float = 0.5,
                     remove_bg: bool = False,
                     aspect_ratio: Optional[str] = None) -> List[str]:
        """
        Process a single image and save all detected crops.
        
        Args:
            input_path: Path to input image
            output_dir: Directory to save cropped images
            target_classes: Classes to detect
            padding: Padding around detected objects (0.0 to 1.0)
            min_confidence: Minimum detection confidence
            remove_bg: Whether to remove background
            aspect_ratio: Target aspect ratio (e.g., '1:1', '16:9', '4:3', '9:16')
        
        Returns:
            List of output file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        input_file = Path(input_path)
        img = cv2.imread(input_path)
        
        detections = self.detect_subjects(input_path, target_classes)
        detections = [d for d in detections if d['confidence'] >= min_confidence]
        
        output_files = []
        
        for idx, detection in enumerate(detections):
            bbox = self.add_padding(detection['bbox'], img.shape, padding, aspect_ratio)
            cropped = self.crop_image(input_path, bbox, remove_bg)
            
            output_name = f"{input_file.stem}_{detection['class']}_{idx+1}.png"
            output_file = output_path / output_name
            
            cv2.imwrite(str(output_file), cropped)
            output_files.append(str(output_file))
            
            print(f"✓ Saved: {output_file} (confidence: {detection['confidence']:.2f})")
        
        return output_files
    
    def process_batch(self,
                     input_dir: str,
                     output_dir: str,
                     target_classes: List[str] = None,
                     padding: float = 0.1,
                     min_confidence: float = 0.5,
                     remove_bg: bool = False,
                     aspect_ratio: Optional[str] = None) -> dict:
        """Process all images in a directory."""
        input_path = Path(input_dir)
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        
        image_files = [f for f in input_path.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        results = {}
        
        for img_file in image_files:
            print(f"\nProcessing: {img_file.name}")
            try:
                output_files = self.process_image(
                    str(img_file),
                    output_dir,
                    target_classes,
                    padding,
                    min_confidence,
                    remove_bg,
                    aspect_ratio
                )
                results[str(img_file)] = output_files
            except Exception as e:
                print(f"✗ Error processing {img_file.name}: {e}")
                results[str(img_file)] = []
        
        return results


def main():
    parser = argparse.ArgumentParser(description="AI-powered image cropping pipeline")
    parser.add_argument("input", help="Input image or directory")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument("-c", "--classes", nargs="+", default=["person"], 
                       help="Target classes (person, bottle, car, etc.)")
    parser.add_argument("-m", "--model", default="yolov8n.pt", 
                       help="YOLO model (yolov8n.pt, yolov8s.pt, yolov8m.pt)")
    parser.add_argument("-p", "--padding", type=float, default=0.1,
                       help="Padding around crops (0.0-1.0)")
    parser.add_argument("--min-confidence", type=float, default=0.5,
                       help="Minimum detection confidence")
    parser.add_argument("--remove-bg", action="store_true",
                       help="Remove background from crops")
    parser.add_argument("--aspect-ratio", type=str, default=None,
                       help="Target aspect ratio (e.g., 1:1, 16:9, 4:3, 9:16)")
    
    args = parser.parse_args()
    
    pipeline = AutoCropPipeline(args.model, args.remove_bg)
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        pipeline.process_image(
            args.input,
            args.output,
            args.classes,
            args.padding,
            args.min_confidence,
            args.remove_bg,
            args.aspect_ratio
        )
    elif input_path.is_dir():
        results = pipeline.process_batch(
            args.input,
            args.output,
            args.classes,
            args.padding,
            args.min_confidence,
            args.remove_bg,
            args.aspect_ratio
        )
        print(f"\n✓ Processed {len(results)} images")
    else:
        print(f"Error: {args.input} is not a valid file or directory")


if __name__ == "__main__":
    main()
