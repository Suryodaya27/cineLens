# Setup Guide

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup TMDB API Key

**Option A: Using .env file (Recommended)**

```bash
# Copy example file
cp .env.example .env

# Edit .env file and add your API key
nano .env
# or
code .env
```

In `.env` file:
```
TMDB_API_KEY=your_actual_api_key_here
```

**Option B: Environment Variable**

```bash
export TMDB_API_KEY=your_api_key_here
```

**Option C: Command Line Argument**

```bash
python3 tmdb_enrichment.py analysis.json --api-key your_key_here
```

### 3. Get TMDB API Key (Free)

1. Go to https://www.themoviedb.org/signup
2. Create free account
3. Go to https://www.themoviedb.org/settings/api
4. Request API key (choose "Developer")
5. Copy your API key
6. Add to `.env` file

### 4. Verify Setup

```bash
# Test TMDB connection
python3 -c "
from tmdb_enrichment import TMDBEnricher
enricher = TMDBEnricher()
print('✓ TMDB API key loaded successfully!')
"
```

## Complete Installation

### Step-by-Step

```bash
# 1. Clone or download the project
cd image-search

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Setup TMDB API key
cp .env.example .env
# Edit .env and add your TMDB_API_KEY

# 4. Verify Ollama is running (for vision model)
ollama list

# 5. Pull vision model if needed
ollama pull qwen2-vl:8b

# 6. Test the pipeline
python3 agentic_pipeline.py test_image.jpg
```

## Configuration Files

### .env File

Create `.env` in project root:

```bash
# TMDB API Configuration
TMDB_API_KEY=abc123xyz789

# Optional: Other API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Important:** `.env` is in `.gitignore` - your keys are safe!

### Movie Context Files

Store movie contexts in `example_movie_contexts/`:

```bash
# Create new movie context
cat > example_movie_contexts/my_movie.json << 'EOF'
{
  "title": "My Movie",
  "year": "2023",
  "cast": ["Actor 1", "Actor 2"]
}
EOF
```

## Dependencies

### Required

- Python 3.8+
- OpenCV
- PyTorch
- Ultralytics (YOLO)
- Ollama (with vision model)
- requests
- python-dotenv

### Optional

- rembg (for background removal)
- transformers (for OWL-ViT advanced detection)
- openai/anthropic/google-generativeai (for cloud vision models)

## Ollama Setup

### Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### Pull Vision Model

```bash
# Recommended model
ollama pull qwen2-vl:8b

# Alternative models
ollama pull llama3.2-vision:11b
ollama pull llava:13b
```

### Verify Ollama

```bash
ollama list
# Should show qwen2-vl:8b or your chosen model
```

## Directory Structure

```
image-search/
├── .env                          # Your API keys (not in git)
├── .env.example                  # Template for .env
├── agentic_pipeline.py           # Main pipeline
├── tmdb_enrichment.py            # TMDB integration
├── requirements.txt              # Python dependencies
├── prompts_context.json          # AI prompts
├── output_schema.json            # JSON schema
├── example_movie_contexts/       # Movie context files
│   ├── leo.json
│   ├── jawan.json
│   └── pathaan.json
└── final-output/                 # Analysis results
```

## Troubleshooting

### "TMDB API key required"

**Solution:**
```bash
# Check if .env exists
ls -la .env

# Check if key is set
cat .env | grep TMDB_API_KEY

# If not, create .env
cp .env.example .env
# Edit and add your key
```

### "No module named 'dotenv'"

**Solution:**
```bash
pip install python-dotenv
```

### "Ollama connection refused"

**Solution:**
```bash
# Start Ollama
ollama serve

# In another terminal, verify
ollama list
```

### "YOLO model not found"

**Solution:**
```bash
# Models auto-download on first run
# Or manually download
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## Environment Variables

All supported environment variables:

```bash
# TMDB (required for enrichment)
TMDB_API_KEY=your_key

# Optional: Cloud vision models
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: Ollama configuration
OLLAMA_HOST=http://localhost:11434
```

## Testing Setup

### Test 1: Basic Pipeline

```bash
# Should detect objects and analyze
python3 agentic_pipeline.py test_image.jpg
```

### Test 2: TMDB Enrichment

```bash
# Should fetch actor filmography
python3 tmdb_enrichment.py final-output/test_image_complete_analysis.json
```

### Test 3: Movie Context

```bash
# Should improve actor identification
python3 agentic_pipeline.py test_image.jpg \
  --movie "Test Movie" \
  --cast "Test Actor"
```

## Updating

```bash
# Update Python packages
pip install -r requirements.txt --upgrade

# Update Ollama models
ollama pull qwen2-vl:8b

# Update YOLO models (auto-updates on run)
python3 agentic_pipeline.py test.jpg --yolo-model yolov8x.pt
```

## Security Notes

- ✅ `.env` is in `.gitignore` - safe from git
- ✅ Never commit API keys to git
- ✅ Use `.env.example` as template
- ✅ Keep `.env` file permissions restricted: `chmod 600 .env`

## Getting Help

1. Check error messages carefully
2. Verify all dependencies installed: `pip list`
3. Check Ollama is running: `ollama list`
4. Verify TMDB key: `cat .env | grep TMDB`
5. See individual guides:
   - `AGENTIC_README.md` - Pipeline usage
   - `TMDB_GUIDE.md` - TMDB enrichment
   - `MOVIE_CONTEXT_GUIDE.md` - Movie context
   - `SCHEMA_GUIDE.md` - JSON schema

## Quick Reference

```bash
# Complete workflow
cp .env.example .env
# Add TMDB_API_KEY to .env
pip install -r requirements.txt
ollama pull qwen2-vl:8b
python3 agentic_pipeline.py image.jpg
python3 tmdb_enrichment.py final-output/image_complete_analysis.json
```

Done! 🎉
