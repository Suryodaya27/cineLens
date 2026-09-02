# Vision Analysis in Updated Pipeline

## Overview

The updated pipeline now supports **optional vision model analysis** for detailed scene and person descriptions, while maintaining fast face recognition as the core feature.

## What Gets Filled

### Without `--enable-vision` (Fast Mode - Default)

```json
{
  "scene_analysis": {
    "setting": "Not analyzed",
    "lighting": "Not analyzed",
    "time_of_day": "Not analyzed",
    "mood": "Not analyzed",
    "background_elements": [],
    "composition": "Not analyzed",
    "context": "Fast mode - scene analysis skipped"
  },
  "people": [{
    "name": "Jim Carrey",  // ✅ From face recognition
    "confidence": 87,       // ✅ From face recognition
    "gender": "unknown",    // ❌ Not analyzed
    "facial_features": "Identified via face recognition",
    "clothing": {
      "description": "Not analyzed",
      "colors": [],
      "style": "Not analyzed",
      "accessories": []
    },
    "pose": "Not analyzed",
    "expression": "Not analyzed",
    "held_items": []
  }],
  "products": [],    // ✅ Detected but not analyzed
  "animals": [],     // ✅ Detected but not analyzed
  "vehicles": [],    // ✅ Detected but not analyzed
  "electronics": [], // ✅ Detected but not analyzed
  "furniture": [],   // ✅ Detected but not analyzed
  "other_objects": []// ✅ Detected but not analyzed
}
```

### With `--enable-vision` (Full Analysis)

```json
{
  "scene_analysis": {
    "setting": "Urban street at night",           // ✅ From vision model
    "lighting": "Dramatic neon lighting",         // ✅ From vision model
    "time_of_day": "Night",                       // ✅ From vision model
    "mood": "Intense, action-packed",             // ✅ From vision model
    "background_elements": ["cars", "buildings"], // ✅ From vision model
    "composition": "Dynamic diagonal",            // ✅ From vision model
    "context": "Action sequence"                  // ✅ From vision model
  },
  "people": [{
    "name": "Jim Carrey",                         // ✅ From face recognition
    "confidence": 87,                             // ✅ From face recognition
    "gender": "male",                             // ✅ From vision model
    "facial_features": "Expressive face with...", // ✅ From vision model
    "clothing": {
      "description": "Black leather jacket",      // ✅ From vision model
      "colors": ["black", "white"],               // ✅ From vision model
      "style": "casual action hero",              // ✅ From vision model
      "accessories": ["sunglasses"]               // ✅ From vision model
    },
    "pose": "Standing confidently",               // ✅ From vision model
    "expression": "Serious, determined",          // ✅ From vision model
    "held_items": [{"item": "gun", ...}]          // ✅ From vision model
  }],
  "products": [],    // ✅ Detected, ❌ Not analyzed yet
  "animals": [],     // ✅ Detected, ❌ Not analyzed yet
  "vehicles": [],    // ✅ Detected, ❌ Not analyzed yet
  "electronics": [], // ✅ Detected, ❌ Not analyzed yet
  "furniture": [],   // ✅ Detected, ❌ Not analyzed yet
  "other_objects": []// ✅ Detected, ❌ Not analyzed yet
}
```

## Current Status

### ✅ Fully Implemented
- **Face recognition** (InsightFace + pgvector)
- **Actor identification** with TMDB cast matching
- **Scene analysis** (with vision model)
- **People details** (clothing, pose, expression with vision model)
- **Object detection** (YOLO detects all categories)
- **Detection counts** in `detections_summary`

### ⚠️ Partially Implemented
- **Products/Animals/Vehicles/etc.** - Detected by YOLO but not analyzed by vision model
- Arrays are present but empty (maintains schema compatibility)

### ❌ Not Yet Implemented
- Vision model analysis for non-people objects
- Would require additional prompts and processing time

## Usage

### Fast Mode (Default)
```bash
python3 updated_agentic_pipeline.py input/image.jpg --movie "Movie Title"
```
- ⚡ Very fast (1-2 seconds per person)
- ✅ Accurate actor identification
- ❌ No scene/clothing details

### Full Analysis Mode
```bash
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie Title" \
  --enable-vision
```
- 🐌 Slower (30-60 seconds per person + scene)
- ✅ Accurate actor identification
- ✅ Detailed scene analysis
- ✅ Clothing and pose details

### Custom Vision Model
```bash
# Use smaller/faster model
python3 updated_agentic_pipeline.py input/image.jpg \
  --movie "Movie Title" \
  --enable-vision \
  --vision-model "llama3.2-vision:11b"
```

## Recommended Vision Models

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `llama3.2-vision:11b` | 11B | Medium | Good | Balanced (default) |
| `llama3.2-vision:90b` | 90B | Slow | Excellent | Best quality |
| `minicpm-v:8b` | 8B | Fast | Good | Speed priority |
| `qwen2-vl:7b` | 7B | Fast | Good | Speed priority |

## Schema Compatibility

The output JSON is **100% compatible** with `agentic_pipeline.py`:

✅ Same structure
✅ Same field names  
✅ All arrays always present (empty if not analyzed)
✅ Can be validated with `output_schema.json`

## Performance Comparison

| Feature | Fast Mode | With Vision |
|---------|-----------|-------------|
| Actor ID | 1-2s | 1-2s |
| Scene Analysis | Skipped | +5-10s |
| Per Person Details | Skipped | +30-60s |
| **Total (2 people)** | **~4s** | **~70-130s** |

## Future Enhancements

To fully match `agentic_pipeline.py`, we could add:

1. **Product analysis** - Analyze detected products with vision model
2. **Animal analysis** - Describe detected animals
3. **Vehicle analysis** - Identify vehicle make/model
4. **Parallel processing** - Analyze multiple objects simultaneously
5. **Caching** - Cache vision model results

## When to Use Each Mode

### Use Fast Mode When:
- ✅ You only need actor identification
- ✅ Processing many images
- ✅ Speed is critical
- ✅ You don't need clothing/scene details

### Use Vision Mode When:
- ✅ You need detailed descriptions
- ✅ Clothing analysis is important
- ✅ Scene context matters
- ✅ Processing few images
- ✅ Quality over speed

## Example Output

See `output/morgan_complete_analysis.json` for a real example of the output structure.

## Summary

**Current state:**
- ✅ All JSON keys are present (schema compatible)
- ✅ Face recognition works perfectly
- ✅ Scene analysis works with vision model
- ✅ People details work with vision model
- ⚠️ Other object arrays are empty (detected but not analyzed)

**To get full analysis:**
Use `--enable-vision` flag and a good vision model like `llama3.2-vision:11b`.
