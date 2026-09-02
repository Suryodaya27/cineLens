# Agentic AI Pipeline

## Overview

This is a fully-fledged intelligent image analysis system that:

1. **Detects ALL objects** using YOLO (people, products, animals, vehicles, electronics, furniture, etc.)
2. **Uses specialized prompts** for each object type (different prompt for bottles vs people vs cars)
3. **Analyzes scene context** once and uses it for all objects
4. **Processes in parallel** for speed
5. **Outputs structured JSON** with complete analysis

## Key Features

### 🎯 Intelligent Object Detection
- Detects 80+ object classes
- Categorizes into: people, products, animals, vehicles, electronics, furniture
- Uses specialized analysis prompts for each category

### 🧠 Context-Aware Analysis
- Analyzes scene once (lighting, setting, mood)
- Uses context when analyzing individual objects
- Understands relationships (person holding bottle)

### ⚡ Parallel Processing
- Analyzes multiple objects simultaneously
- Configurable thread count
- Much faster than sequential processing

### 📦 Specialized Prompts
- **People**: Identifies actors/celebrities, describes clothing, held items
- **Bottles**: Identifies brand, type (Pepsi, Coca-Cola, wine, etc.)
- **Animals**: Identifies breed, characteristics
- **Vehicles**: Identifies make, model, year
- **Electronics**: Identifies brand, model (iPhone, MacBook, etc.)
- And more...

## Usage

### Basic Usage
```bash
# Analyze everything in the image
python3 agentic_pipeline.py actor_with_pepsi.jpg
```

**Output will include:**
- Actor identification and clothing
- Pepsi bottle brand and type
- Scene context
- All other visible objects

### Advanced Usage

```bash
# Use more threads for faster processing
python3 agentic_pipeline.py group_photo.jpg --threads 4

# Just describe people, don't identify by name
python3 agentic_pipeline.py photo.jpg --no-identify

# Custom output directory
python3 agentic_pipeline.py photo.jpg -o my-results/

# Use better YOLO model for more accurate detection
python3 agentic_pipeline.py photo.jpg --yolo-model yolov8m.pt

# Adjust detection sensitivity
python3 agentic_pipeline.py photo.jpg --min-confidence 0.7
```

## Output Structure

Results saved to `final-output/image_complete_analysis.json`:

```json
{
  "source_image": "actor_with_pepsi.jpg",
  "scene_analysis": {
    "setting": "Indoor studio with professional lighting",
    "lighting": "Bright, professional studio lighting",
    "time_of_day": "Indeterminate (studio)",
    "mood": "Professional, promotional",
    "background_elements": ["white backdrop", "studio equipment"],
    "composition": "Centered subject with product placement",
    "context": "Professional photo shoot or advertisement"
  },
  "detections_summary": {
    "people": 1,
    "products": 1
  },
  "people": [
    {
      "name": "Shah Rukh Khan",
      "profession": "Bollywood actor",
      "facial_features": "Distinctive facial structure...",
      "clothing": "Black leather jacket, white t-shirt",
      "pose": "Standing, facing camera",
      "expression": "Confident smile",
      "held_items": "Pepsi bottle in right hand",
      "confidence": 95,
      "object_class": "person",
      "crop_image": "final-output/actor_with_pepsi_person_1.png",
      "detection_confidence": 0.98
    }
  ],
  "products": [
    {
      "brand": "Pepsi",
      "product_type": "soda",
      "size": "500ml bottle",
      "material": "plastic",
      "color": "blue label, clear bottle",
      "label_text": "PEPSI",
      "condition": "new, sealed",
      "distinctive_features": "Classic Pepsi blue and red logo",
      "object_class": "bottle",
      "crop_image": "final-output/actor_with_pepsi_bottle_1.png",
      "detection_confidence": 0.92
    }
  ]
}
```

## Example Scenarios

### Scenario 1: Actor with Product
```bash
python3 agentic_pipeline.py celebrity_endorsement.jpg
```
**Detects:**
- Actor (identifies by name, describes outfit)
- Product they're holding (brand, type)
- Scene context

### Scenario 2: Event Photo
```bash
python3 agentic_pipeline.py party.jpg --threads 4
```
**Detects:**
- All people (identifies celebrities)
- Drinks/bottles (brands)
- Furniture (tables, chairs)
- Electronics (phones, cameras)

### Scenario 3: Product Catalog
```bash
python3 agentic_pipeline.py products.jpg
```
**Detects:**
- All products with brands
- Detailed descriptions
- Colors, materials, conditions

### Scenario 4: Street Scene
```bash
python3 agentic_pipeline.py street.jpg
```
**Detects:**
- People
- Vehicles (make, model, color)
- Signs and objects
- Scene context

## Prompt Customization

Edit `prompts_context.json` to customize prompts for each object type:

```json
{
  "bottle": {
    "prompt": "Your custom prompt for bottles...",
    "description": "What this prompt does"
  }
}
```

## Performance Tips

1. **More threads = faster** (but uses more resources)
   - 2-3 threads: Good balance
   - 4-6 threads: Fast for many objects
   - 1 thread: Slower but less resource intensive

2. **YOLO model selection:**
   - `yolov8n.pt`: Fastest, good accuracy
   - `yolov8m.pt`: Balanced
   - `yolov8x.pt`: Most accurate, slower

3. **Confidence threshold:**
   - Lower (0.3-0.4): Detects more objects, some false positives
   - Default (0.5): Good balance
   - Higher (0.6-0.7): Only high-confidence detections

## Comparison with Other Pipelines

| Feature | smart_pipeline.py | agentic_pipeline.py |
|---------|------------------|---------------------|
| Detects people | ✅ | ✅ |
| Detects products | ❌ | ✅ |
| Detects animals | ❌ | ✅ |
| Detects vehicles | ❌ | ✅ |
| Specialized prompts | ❌ | ✅ |
| Held items detection | ❌ | ✅ |
| Complete scene analysis | ✅ | ✅ |

## Requirements

- Python 3.8+
- Ollama with vision model (qwen2-vl:8b recommended)
- YOLO model (auto-downloads)
- See requirements.txt for packages

## Tips

- For best results with celebrity identification, use a larger vision model
- The pipeline automatically categorizes objects for appropriate analysis
- All crops are saved for manual review
- JSON output is structured for easy parsing and integration
