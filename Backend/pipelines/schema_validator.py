#!/usr/bin/env python3
"""
Schema validator and normalizer for agentic pipeline output.
Ensures all JSON outputs have consistent structure.
"""

import json
from typing import Dict, Any
from pathlib import Path


class OutputNormalizer:
    """Normalizes analysis output to match fixed schema."""
    
    @staticmethod
    def normalize_person(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize person object to match schema."""
        return {
            "name": data.get("name"),
            "profession": data.get("profession"),
            "gender": data.get("gender", "unknown"),
            "facial_features": data.get("facial_features", ""),
            "clothing": OutputNormalizer._normalize_clothing(data.get("clothing", {})),
            "pose": data.get("pose", ""),
            "expression": data.get("expression", ""),
            "held_items": OutputNormalizer._normalize_held_items(data.get("held_items", [])),
            "confidence": data.get("confidence", 0),
            "object_class": data.get("object_class", "person"),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def _normalize_clothing(clothing: Any) -> Dict[str, Any]:
        """Normalize clothing to structured format."""
        if isinstance(clothing, str):
            # Convert string to structured format
            return {
                "description": clothing,
                "colors": [],
                "style": "unknown",
                "accessories": []
            }
        elif isinstance(clothing, dict):
            return {
                "description": clothing.get("description", ""),
                "colors": clothing.get("colors", []) if isinstance(clothing.get("colors"), list) else [],
                "style": clothing.get("style", "unknown"),
                "accessories": clothing.get("accessories", []) if isinstance(clothing.get("accessories"), list) else []
            }
        else:
            return {
                "description": "",
                "colors": [],
                "style": "unknown",
                "accessories": []
            }
    
    @staticmethod
    def _normalize_held_items(held_items: Any) -> list:
        """Normalize held_items to array format."""
        if isinstance(held_items, str):
            # Convert string to array
            if held_items and held_items.lower() not in ["none", "null", "nothing"]:
                return [{"item": held_items, "description": held_items}]
            return []
        elif isinstance(held_items, list):
            normalized = []
            for item in held_items:
                if isinstance(item, str):
                    normalized.append({"item": item, "description": item})
                elif isinstance(item, dict):
                    normalized.append({
                        "item": item.get("item", ""),
                        "description": item.get("description", "")
                    })
            return normalized
        return []
    
    @staticmethod
    def normalize_product(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize product object to match schema."""
        return {
            "brand": data.get("brand"),
            "product_type": data.get("product_type", "unknown"),
            "size": data.get("size", "unknown"),
            "material": data.get("material", "unknown"),
            "color": data.get("color", []) if isinstance(data.get("color"), list) else [data.get("color", "")],
            "label_text": data.get("label_text"),
            "condition": data.get("condition", "unknown"),
            "distinctive_features": data.get("distinctive_features", ""),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_animal(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize animal object to match schema."""
        return {
            "breed": data.get("breed", "unknown"),
            "size": data.get("size", "unknown"),
            "color": data.get("color", []) if isinstance(data.get("color"), list) else [data.get("color", "")],
            "age_estimate": data.get("age_estimate", "unknown"),
            "activity": data.get("activity", ""),
            "distinctive_features": data.get("distinctive_features", ""),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_vehicle(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize vehicle object to match schema."""
        return {
            "make": data.get("make"),
            "model": data.get("model"),
            "year_range": data.get("year_range", "unknown"),
            "color": data.get("color", "unknown"),
            "body_type": data.get("body_type", "unknown"),
            "condition": data.get("condition", "unknown"),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_electronics(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize electronics object to match schema."""
        return {
            "brand": data.get("brand"),
            "model": data.get("model"),
            "type": data.get("type", "unknown"),
            "color": data.get("color", "unknown"),
            "condition": data.get("condition", "unknown"),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_furniture(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize furniture object to match schema."""
        return {
            "type": data.get("type", "unknown"),
            "material": data.get("material", "unknown"),
            "style": data.get("style", "unknown"),
            "color": data.get("color", []) if isinstance(data.get("color"), list) else [data.get("color", "")],
            "condition": data.get("condition", "unknown"),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_other_object(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize other object to match schema."""
        return {
            "type": data.get("type", "unknown"),
            "brand": data.get("brand"),
            "color": data.get("color", []) if isinstance(data.get("color"), list) else [data.get("color", "")],
            "material": data.get("material", "unknown"),
            "condition": data.get("condition", "unknown"),
            "distinctive_features": data.get("distinctive_features", ""),
            "context": data.get("context", ""),
            "object_class": data.get("object_class", ""),
            "crop_image": data.get("crop_image", ""),
            "detection_confidence": data.get("detection_confidence", 0.0)
        }
    
    @staticmethod
    def normalize_scene_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize scene analysis to match schema."""
        return {
            "setting": data.get("setting", "unknown"),
            "lighting": data.get("lighting", "unknown"),
            "time_of_day": data.get("time_of_day", "unknown"),
            "mood": data.get("mood", "unknown"),
            "background_elements": data.get("background_elements", []) if isinstance(data.get("background_elements"), list) else [],
            "composition": data.get("composition", ""),
            "context": data.get("context", "")
        }
    
    @staticmethod
    def normalize_output(result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize complete output to match fixed schema."""
        normalized = {
            "source_image": result.get("source_image", ""),
            "scene_analysis": OutputNormalizer.normalize_scene_analysis(result.get("scene_analysis", {})),
            "detections_summary": {
                "people": len(result.get("people", [])),
                "products": len(result.get("products", [])),
                "animals": len(result.get("animals", [])),
                "vehicles": len(result.get("vehicles", [])),
                "electronics": len(result.get("electronics", [])),
                "furniture": len(result.get("furniture", [])),
                "other_objects": len(result.get("other_objects", []))
            },
            "people": [OutputNormalizer.normalize_person(p) for p in result.get("people", [])],
            "products": [OutputNormalizer.normalize_product(p) for p in result.get("products", [])],
            "animals": [OutputNormalizer.normalize_animal(a) for a in result.get("animals", [])],
            "vehicles": [OutputNormalizer.normalize_vehicle(v) for v in result.get("vehicles", [])],
            "electronics": [OutputNormalizer.normalize_electronics(e) for e in result.get("electronics", [])],
            "furniture": [OutputNormalizer.normalize_furniture(f) for f in result.get("furniture", [])],
            "other_objects": [OutputNormalizer.normalize_other_object(o) for o in result.get("other_objects", [])]
        }
        
        return normalized


def validate_and_fix_json(json_file: str) -> Dict[str, Any]:
    """Load JSON file, normalize it, and save back."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    normalized = OutputNormalizer.normalize_output(data)
    
    # Save normalized version
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Normalized and saved: {json_file}")
    return normalized


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate and normalize JSON output")
    parser.add_argument("json_file", help="JSON file to normalize")
    
    args = parser.parse_args()
    
    validate_and_fix_json(args.json_file)
