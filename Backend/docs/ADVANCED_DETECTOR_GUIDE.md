# Advanced Detector Guide

## Purpose

`advanced_detector.py` is a **standalone tool** for detecting objects that YOLO misses (guitars, instruments, accessories, etc.). It does NOT replace `agentic_pipeline.py`.

## When to Use

Use `advanced_detector.py` when:
- ✅ YOLO misses objects (guitars, instruments, jewelry)
- ✅ You need to detect custom objects
- ✅ You want to compare detection models
- ✅ You need open-vocabulary detection

Continue using `agentic_pipeline.py` for:
- ✅ Complete image analysis with vision LLM
- ✅ Actor identification
- ✅ Product brand recognition
- ✅ Scene analysis

## Installation

```bash
# For OWL-ViT (recommended)
pip install transformers torch torchvision pillow

# Verify installation
python3 -c "from transformers import OwlViTProcessor; print('✓ Ready')"
```

## Basic Usage

### 1. Detect Guitars and Instruments
```bash
python3 advanced_detector.py musician_photo.jpg \
  --model owl-vit \
  --prompts person guitar microphone drum
```

**Output:**
```
✅ Detected 4 objects:

  PERSON: 1
    1. Confidence: 0.85

  GUITAR: 1
    1. Confidence: 0.72

  MICROPHONE: 1
    1. Confidence: 0.68

  DRUM: 1
    1. Confidence: 0.45
```

### 2. Compare YOLO vs OWL-ViT
```bash
python3 advanced_detector.py chris_guitar.jpg --compare
```

Shows what each model detects side-by-side.

### 3. Detect with Visualization
```bash
python3 advanced_detector.py image.jpg \
  --model owl-vit \
  --prompts guitar bottle phone \
  --visualize
```

Creates `detected_image.jpg` with bounding boxes drawn.

### 4. Save Results to JSON
```bash
python3 advanced_detector.py image.jpg \
  --model owl-vit \
  --prompts guitar microphone \
  --output detections.json
```

## Common Use Cases

### Musician Photos
```bash
python3 advanced_detector.py musician.jpg \
  --prompts person guitar microphone drum piano violin bass saxophone
```

### Fashion/Accessories
```bash
python3 advanced_detector.py fashion.jpg \
  --prompts person sunglasses watch jewelry bag hat shoes
```

### Sports Equipment
```bash
python3 advanced_detector.py sports.jpg \
  --prompts person tennis_racket basketball football helmet gloves
```

### Office/Workspace
```bash
python3 advanced_detector.py desk.jpg \
  --prompts laptop phone keyboard mouse monitor notebook pen coffee_cup
```

### Party/Event
```bash
python3 advanced_detector.py party.jpg \
  --prompts person bottle glass cup cake balloon decoration
```

## Workflow Integration

### Option 1: Use Both Tools
```bash
# Step 1: Run agentic pipeline (identifies actors, analyzes scene)
python3 agentic_pipeline.py actor_with_guitar.jpg

# Step 2: Run advanced detector (finds guitar YOLO missed)
python3 advanced_detector.py actor_with_guitar.jpg \
  --prompts guitar --output guitar_detection.json

# Step 3: Combine results manually
```

### Option 2: Check What YOLO Missed
```bash
# Compare to see what YOLO missed
python3 advanced_detector.py image.jpg --compare
```

## Tips

### 1. Adjust Confidence Threshold
```bash
# Lower threshold = more detections (may include false positives)
python3 advanced_detector.py image.jpg --confidence 0.1

# Higher threshold = fewer, more confident detections
python3 advanced_detector.py image.jpg --confidence 0.4
```

### 2. Be Specific with Prompts
```bash
# Good: Specific instrument types
--prompts "acoustic guitar" "electric guitar" "bass guitar"

# Less good: Generic
--prompts guitar
```

### 3. Use Default Prompts
```bash
# If no prompts provided, uses comprehensive default list
python3 advanced_detector.py image.jpg --model owl-vit
```

Default prompts include:
- People: person
- Instruments: guitar, microphone, drum, piano, violin
- Products: bottle, cup, phone, laptop
- Accessories: bag, watch, sunglasses, hat
- More...

## Performance

| Model | Speed | Accuracy | Guitar Detection |
|-------|-------|----------|------------------|
| YOLO | ⚡⚡⚡⚡⚡ | Good | ❌ |
| OWL-ViT | ⚡⚡⚡ | Good | ✅ |

**Processing Time:**
- YOLO: ~0.5-1s per image
- OWL-ViT: ~3-5s per image

## Limitations

### OWL-ViT
- ✅ Detects custom objects
- ⚠️ Slower than YOLO
- ⚠️ May have false positives with low confidence
- ⚠️ Requires text prompts

### When It Won't Help
- Very small objects (< 20x20 pixels)
- Heavily occluded objects
- Very blurry images
- Objects not in prompts list

## Troubleshooting

### "ModuleNotFoundError: No module named 'transformers'"
```bash
pip install transformers torch
```

### "Out of memory"
```bash
# Use CPU instead of GPU
export CUDA_VISIBLE_DEVICES=""
python3 advanced_detector.py image.jpg
```

### Too many false positives
```bash
# Increase confidence threshold
python3 advanced_detector.py image.jpg --confidence 0.4
```

### Missing detections
```bash
# Lower confidence threshold
python3 advanced_detector.py image.jpg --confidence 0.1

# Add more specific prompts
--prompts "acoustic guitar" "electric guitar" "classical guitar"
```

## Examples

### Example 1: Musician with Guitar
```bash
python3 advanced_detector.py chris_guitar.jpg \
  --model owl-vit \
  --prompts person guitar microphone \
  --visualize \
  --output chris_detections.json
```

**Result:**
- Detects person ✅
- Detects guitar ✅ (YOLO missed this!)
- Saves visualization with boxes
- Saves JSON with coordinates

### Example 2: Product Shoot
```bash
python3 advanced_detector.py products.jpg \
  --prompts bottle can glass cup label logo \
  --visualize
```

### Example 3: Concert Photo
```bash
python3 advanced_detector.py concert.jpg \
  --prompts person guitar bass drum microphone speaker amplifier \
  --confidence 0.3
```

## Summary

- **Use `agentic_pipeline.py`** for complete AI analysis (actor ID, scene, products)
- **Use `advanced_detector.py`** when you need to detect specific objects YOLO misses
- **Use `--compare`** to see what each model detects
- **OWL-ViT is recommended** for open-vocabulary detection
- **Keep both tools** - they serve different purposes!
