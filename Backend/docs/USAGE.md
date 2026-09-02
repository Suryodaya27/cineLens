# Smart Pipeline Usage Guide

## Overview
The smart pipeline analyzes images intelligently:
1. First analyzes the full image for background and products
2. Detects and crops each person individually
3. Identifies each person with context from the scene
4. Outputs structured JSON with all information

## Basic Usage

```bash
# Analyze an image (identifies people by name if possible)
python3 smart_pipeline.py image.jpg

# Just describe people, don't identify names
python3 smart_pipeline.py image.jpg --no-identify

# Custom output directory
python3 smart_pipeline.py image.jpg -o my-results/

# With aspect ratio for crops
python3 smart_pipeline.py image.jpg --aspect-ratio 1:1
```

## Output Structure

Results are saved to `final-output/image_analysis.json`:

```json
{
  "source_image": "photo.jpg",
  "background_info": "Indoor restaurant setting with warm lighting",
  "scene_type": "indoor dining",
  "products": ["wine bottles", "dining table", "wine glasses"],
  "people": [
    {
      "actor_name": "Shah Rukh Khan",
      "actor_description": "Male with distinctive facial features...",
      "clothing": "Black formal suit with white shirt",
      "pose": "Standing, facing camera",
      "confidence": 95,
      "crop_image": "final-output/photo_person_1.png",
      "detection_confidence": 0.98
    },
    {
      "actor_name": null,
      "actor_description": "Male with short dark hair...",
      "clothing": "Blue casual shirt",
      "pose": "Seated position",
      "crop_image": "final-output/photo_person_2.png",
      "detection_confidence": 0.92
    }
  ]
}
```

## Key Features

- **Smart Context**: Analyzes scene once, uses context for all people
- **Structured Output**: Clean JSON format, easy to parse
- **Confidence Filtering**: Only shows actor names if 90%+ confident
- **Minimal Terminal Output**: Clean progress indicators
- **Separate Crops**: Each person gets individual analysis

## Examples

```bash
# Movie poster analysis
python3 smart_pipeline.py poster.jpg --aspect-ratio 2:3

# Event photo with products
python3 smart_pipeline.py event.jpg

# Just describe appearance
python3 smart_pipeline.py photo.jpg --no-identify

# Use better YOLO model
python3 smart_pipeline.py photo.jpg --yolo-model yolov8m.pt
```

## Output Files

- `final-output/image_analysis.json` - Complete analysis
- `final-output/image_person_1.png` - First person crop
- `final-output/image_person_2.png` - Second person crop
- etc.
