# Vision Model Configuration

Guide for configuring the vision model used in the API.

## Overview

The vision model is used when `enable_vision=1` in the API request. It provides detailed analysis of:
- Scene setting, lighting, mood
- Person clothing, pose, expression
- Product brands, materials, features
- Animal breeds, activities
- Vehicle makes, models

## Configuration Options

### 1. Environment Variable (Default for all requests)

Set in `.env` file:

```bash
VISION_MODEL=llama3.2-vision:11b
```

This becomes the default model for all API requests when `vision_model` is not specified.

**Available Models:**
- `llama3.2-vision:11b` (default) - Best quality, slower
- `qwen3-vl:8b` - Good quality, faster
- `llava:13b` - Alternative option
- `llava:7b` - Faster, lower quality

### 2. Per-Request Override

Specify in the API request body:

```json
{
  "image_url": "https://example.com/image.jpg",
  "movie_name": "Pathaan",
  "enable_vision": 1,
  "vision_model": "qwen3-vl:8b"
}
```

This overrides the default for this specific request.

## Usage Examples

### Using Default Model

```bash
# Uses VISION_MODEL from .env (llama3.2-vision:11b)
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 1
  }'
```

### Using Custom Model

```bash
# Uses qwen3-vl:8b for this request
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "movie_name": "Pathaan",
    "enable_vision": 1,
    "vision_model": "qwen3-vl:8b"
  }'
```

### Python Client

```python
import requests

# Using default model
response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "image_url": "https://example.com/image.jpg",
        "movie_name": "Pathaan",
        "enable_vision": 1
    }
)

# Using custom model
response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "image_url": "https://example.com/image.jpg",
        "movie_name": "Pathaan",
        "enable_vision": 1,
        "vision_model": "qwen3-vl:8b"
    }
)
```

## Model Comparison

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| llama3.2-vision:11b | 11B | Slow | Best | Production, high accuracy needed |
| qwen3-vl:8b | 8B | Medium | Good | Balanced speed/quality |
| llava:13b | 13B | Slow | Good | Alternative to Llama |
| llava:7b | 7B | Fast | Fair | Development, testing |

## Installation

Vision models require Ollama to be installed and running:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a vision model
ollama pull llama3.2-vision:11b
ollama pull qwen3-vl:8b

# Verify it's running
ollama list
```

## Configuration Files

### .env
```bash
# Vision Model Configuration
VISION_MODEL=llama3.2-vision:11b
```

### api.py
```python
# Default vision model from environment
DEFAULT_VISION_MODEL = os.getenv('VISION_MODEL', 'llama3.2-vision:11b')

# Used when initializing pipeline
pipeline = UpdatedAgenticPipeline(
    yolo_model="yolov8n.pt",
    vision_model=request.vision_model or DEFAULT_VISION_MODEL,
    use_vision_analysis=bool(request.enable_vision)
)
```

## Troubleshooting

### "Vision model not found"
```bash
# Pull the model
ollama pull llama3.2-vision:11b
```

### "Ollama not running"
```bash
# Start Ollama service
ollama serve
```

### "Model too slow"
Try a smaller model:
```bash
# Use faster model
ollama pull qwen3-vl:8b
```

Then set in `.env`:
```bash
VISION_MODEL=qwen3-vl:8b
```

### Check available models
```bash
ollama list
```

## Performance Tips

1. **Use smaller models for development**: `qwen3-vl:8b` or `llava:7b`
2. **Use larger models for production**: `llama3.2-vision:11b`
3. **Cache results**: Store analysis results to avoid re-processing
4. **Disable vision when not needed**: Set `enable_vision=0` for faster processing

## Command Line Usage

The vision model can also be specified in command line scripts:

```bash
# updated_agentic_pipeline.py
python updated_agentic_pipeline.py input.jpg \
  --movie "Pathaan" \
  --enable-vision \
  --vision-model "qwen3-vl:8b"

# agentic_pipeline.py
python agentic_pipeline.py input.jpg \
  --vision-model "llama3.2-vision:11b"
```

## Summary

**Where to configure:**
1. **Global default**: `.env` file → `VISION_MODEL=llama3.2-vision:11b`
2. **Per-request**: API request body → `"vision_model": "qwen3-vl:8b"`
3. **Command line**: Script argument → `--vision-model "qwen3-vl:8b"`

**Priority:**
Request body > Command line argument > Environment variable > Hardcoded default

**Recommendation:**
- Set a good default in `.env` (e.g., `llama3.2-vision:11b`)
- Override per-request when you need different speed/quality trade-offs
