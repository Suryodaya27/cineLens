# AI-Powered Image Cropping Pipeline

Automatically detect and crop actors and products from images using AI.

## 🚀 NEW: REST API Available!

The pipeline is now available as a REST API! Accept image URLs, identify actors, and get hosted crop URLs.

**Quick Start:**
```bash
./start_api.sh
# or
python api.py
```

**API Documentation:** See [API_README.md](API_README.md) and [API_QUICK_START.md](API_QUICK_START.md)

## Features

- **AI Detection**: Uses YOLOv8 for accurate object detection
- **Actor Identification**: Fast face recognition with InsightFace + pgvector
- **Movie Context**: Identifies actors from specific movies/TV series using TMDB
- **REST API**: Accept image URLs and return results with hosted crop URLs
- **Multiple Classes**: Detect people, products, animals, vehicles, etc.
- **Background Removal**: Optional AI-powered background removal
- **Batch Processing**: Process entire directories
- **Vision Analysis**: Optional detailed scene and clothing analysis
- **Configurable Padding**: Add space around detected subjects
- **Confidence Filtering**: Only crop high-confidence detections

## Installation

### For API (Recommended):
```bash
pip install -r requirements_api.txt
```

### For Basic Pipeline:
```bash
pip install -r requirements.txt
```

### For Updated Pipeline (Actor Identification):
```bash
pip install -r requirements_updated_pipeline.txt
```

## Quick Start

### REST API (New!)

```bash
# Start the API server
./start_api.sh

# Test with curl
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 0
  }'
```

See [API_QUICK_START.md](API_QUICK_START.md) for detailed API setup.

### Command Line

### Crop people from a single image:
```bash
python crop_pipeline.py input.jpg -o output/
```

### Crop products (bottles, cars, etc.):
```bash
python crop_pipeline.py input.jpg -o output/ -c bottle car cup
```

### Process entire directory with background removal:
```bash
python crop_pipeline.py input_folder/ -o output/ --remove-bg
```

### Advanced options:
```bash
python crop_pipeline.py input.jpg \
  -o output/ \
  -c person \
  -m yolov8m.pt \
  -p 0.15 \
  --min-confidence 0.7 \
  --remove-bg
```

## Options

- `-o, --output`: Output directory (default: output)
- `-c, --classes`: Target classes to detect (default: person)
- `-m, --model`: YOLO model size (yolov8n/s/m/l/x.pt)
- `-p, --padding`: Padding around crops 0.0-1.0 (default: 0.1)
- `--min-confidence`: Minimum detection confidence (default: 0.5)
- `--remove-bg`: Remove background from crops

## Supported Classes

Common classes: person, bicycle, car, motorcycle, bottle, cup, chair, couch, potted plant, bed, dining table, tv, laptop, mouse, keyboard, cell phone, book, clock, vase, scissors, teddy bear, hair drier, toothbrush

[Full COCO dataset class list](https://docs.ultralytics.com/datasets/detect/coco/)

## Python API

```python
from crop_pipeline import AutoCropPipeline

pipeline = AutoCropPipeline(model_name="yolov8n.pt", use_bg_removal=True)

# Process single image
output_files = pipeline.process_image(
    "input.jpg",
    "output/",
    target_classes=["person"],
    padding=0.1,
    min_confidence=0.5,
    remove_bg=True
)

# Process batch
results = pipeline.process_batch(
    "input_folder/",
    "output/",
    target_classes=["person", "bottle"],
    padding=0.15,
    min_confidence=0.6
)
```

## Model Selection

- `yolov8n.pt`: Fastest, smallest (3MB)
- `yolov8s.pt`: Small, balanced
- `yolov8m.pt`: Medium, more accurate
- `yolov8l.pt`: Large, high accuracy
- `yolov8x.pt`: Extra large, best accuracy

First run downloads the model automatically.

## Available Pipelines

This project includes multiple pipelines for different use cases:

### 1. REST API (`api.py`) - **RECOMMENDED**
- **Use Case**: Production applications, web services
- **Features**: Accept image URLs, identify actors, return hosted crop URLs
- **Speed**: Fast (5-15s per image)
- **Setup**: See [API_QUICK_START.md](API_QUICK_START.md)
- **Documentation**: [API_README.md](API_README.md)

### 2. Updated Agentic Pipeline (`updated_agentic_pipeline.py`)
- **Use Case**: Actor identification with movie context
- **Features**: InsightFace + pgvector for fast face recognition
- **Speed**: Fast (5-15s per image)
- **Setup**: See [docs/UPDATED_PIPELINE_SETUP.md](docs/UPDATED_PIPELINE_SETUP.md)
- **Documentation**: [docs/UPDATED_PIPELINE_README.md](docs/UPDATED_PIPELINE_README.md)

### 3. Agentic Pipeline (`agentic_pipeline.py`)
- **Use Case**: Detailed analysis with vision models
- **Features**: Full scene analysis, clothing details, product identification
- **Speed**: Slower (30-90s per image)
- **Documentation**: [docs/AGENTIC_README.md](docs/AGENTIC_README.md)

### 4. Basic Crop Pipeline (`crop_pipeline.py`)
- **Use Case**: Simple object detection and cropping
- **Features**: Fast YOLO-based detection, no identification
- **Speed**: Very fast (1-3s per image)
- **Documentation**: This README

## Documentation

- **API**: [API_README.md](API_README.md) | [API_QUICK_START.md](API_QUICK_START.md)
- **Updated Pipeline**: [docs/UPDATED_PIPELINE_README.md](docs/UPDATED_PIPELINE_README.md)
- **Setup Guide**: [docs/UPDATED_PIPELINE_SETUP.md](docs/UPDATED_PIPELINE_SETUP.md)
- **Agentic Pipeline**: [docs/AGENTIC_README.md](docs/AGENTIC_README.md)
- **Pipeline Comparison**: [docs/compare_pipelines.md](docs/compare_pipelines.md)
