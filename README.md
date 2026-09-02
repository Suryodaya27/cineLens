# CineLens AI

AI-powered movie scene analysis — identify actors, detect objects, analyze scenes, and find shopping links from a single movie frame.

## Highlights

- **Situation:** Movie and entertainment platforms need to extract structured metadata from video frames — who's on screen, what they're wearing, what objects are visible — but manual tagging doesn't scale and generic vision APIs lack movie-specific context.

- **Task:** Build an end-to-end system that takes a movie frame + movie name, identifies the specific actors from that film's cast, describes the scene in detail, and connects detected items to purchasable products — all with real-time progress feedback.

- **Action:** Combined YOLOv8 object detection with InsightFace face recognition and pgvector similarity search against TMDB cast embeddings. Added an optional local vision LLM (Ollama) for scene/clothing/object analysis with scene-context injection to correct YOLO misclassifications. Built SSE streaming from FastAPI through Next.js to show live pipeline progress.

- **Result:** Actors identified at 74–95% confidence in under 10 seconds (face matching only). Full vision analysis with scene descriptions, clothing details, and object analysis in 2–8 minutes on local hardware. Shopping recommendations via Amazon text search + SerpAPI visual search. All with a live progress UI instead of a blank loading screen.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser — Next.js (localhost:3000)                                  │
│  ┌────────────┐  ┌───────────────────────────────────────────────┐  │
│  │ Input Panel │  │ Output Panel                                 │  │
│  │ movie name  │  │ live SSE progress → results display          │  │
│  │ + image     │  │                                               │  │
│  └──────┬──────┘  └─────────────────────────▲─────────────────────┘  │
└─────────┼───────────────────────────────────┼────────────────────────┘
          │ POST /api/analyze-movie           │ SSE stream
          ▼                                   │
┌──────────────────────────────────────────────────────────────────────┐
│  Next.js API Route                                                   │
│  1. Upload image to ImgBB   2. Open SSE to backend                  │
│  3. Proxy all events to browser                                      │
└──────────────────────┬──────────────────────▲────────────────────────┘
                       │ SSE                  │
                       ▼                      │
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (localhost:8000)                                     │
│                                                                      │
│  Download → Init YOLO+InsightFace → TMDB cast lookup                │
│  → YOLO detect → Face match via pgvector                            │
│  → Vision LLM analysis (optional) → Upload crops to ImgBB           │
│  → Stream "complete" event with full result                          │
└───────────┬──────────────────┬──────────────────┬────────────────────┘
            ▼                  ▼                  ▼
   PostgreSQL+pgvector     TMDB API         Ollama (local LLM)
   (face embeddings)    (cast, images)     (scene/object analysis)
```

**SSE event flow:** The pipeline streams progress events (`imagebb` → `progress` × N → `complete` or `error`) so the UI updates step-by-step: upload → download → init → cast → detect → identify → scene → objects → upload crops.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, Tailwind CSS, SSE streaming |
| Backend | FastAPI, Uvicorn |
| Object detection | YOLOv8 |
| Face recognition | InsightFace (512-dim embeddings) |
| Vector search | PostgreSQL + pgvector |
| Cast data | TMDB API |
| Vision analysis | Ollama (qwen3.8, llama3.2-vision, etc.) |
| Image hosting | ImgBB |
| Shopping | Amazon scraping + SerpAPI visual search |

## Project Structure

```
├── Frontend/                        Next.js app
│   ├── app/page.tsx                 Main page (SSE progress + results)
│   ├── app/api/analyze-movie/       API route (ImgBB upload + SSE proxy)
│   ├── components/input-panel.tsx   Movie name + image input
│   └── components/output-panel.tsx  Results display
│
├── Backend/
│   ├── api.py                       FastAPI entry point (/analyze, /analyze-stream)
│   ├── pipelines/                   ML modules
│   │   ├── updated_agentic_pipeline.py  YOLO + InsightFace + vision LLM
│   │   ├── crop_pipeline.py             YOLO cropping
│   │   └── vision_classifier.py         Multi-provider vision classifier
│   ├── services/                    Business logic
│   │   ├── unified_shopping.py      Shopping orchestrator
│   │   ├── amazon_shopping.py       Amazon text search
│   │   ├── visual_search.py         SerpAPI visual search
│   │   └── tmdb_enrichment.py       TMDB actor enrichment
│   ├── scripts/                     Debug utilities
│   ├── tests/                       Integration tests
│   └── docs/                        Detailed documentation
```

## Prerequisites

**Runtime:** Python 3.8+, Node.js 20+, Docker

**API keys (all free):**
- [TMDB](https://www.themoviedb.org/settings/api) — cast data and actor images (required)
- [ImgBB](https://api.imgbb.com/) — image hosting (required)
- [SerpAPI](https://serpapi.com/users/sign_up) — visual product search (optional, 100 free/month)

**Optional:** [Ollama](https://ollama.com) — only needed for vision analysis (`enable_vision=1`)

## Quick Start

### 1. Database

```bash
docker run -d --name pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=face_embeddings \
  -p 5432:5432 pgvector/pgvector:pg16

docker exec pgvector psql -U postgres -c "CREATE DATABASE face_recognition;"
docker exec pgvector psql -U postgres -d face_recognition -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 2. Backend

```bash
cd Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TMDB_API_KEY and IMGBB_API_KEY
python api.py           # → http://localhost:8000
```

### 3. Frontend

```bash
cd Frontend
npm install
cp .env.example .env.local   # fill in IMGBB_API_KEY
npm run dev                   # → http://localhost:3000
```

### 4. Vision model (optional)

```bash
ollama pull qwen3.8:latest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Analyze image (JSON response) |
| POST | `/analyze-stream` | Analyze image (SSE streaming) |
| POST | `/api/more-movies` | Actor filmography from TMDB |
| POST | `/api/shopping-recommendations` | Shopping links for detected items |
| GET | `/health` | Health check |

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/frame.jpg", "movie_name": "Inception", "enable_vision": 0}'
```

## Configuration

Environment variables in `Backend/.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `TMDB_API_KEY` | Yes | Cast data |
| `IMGBB_API_KEY` | Yes | Image hosting |
| `SERPAPI_KEY` | No | Visual product search |
| `VISION_MODEL` | No | Ollama model (default: `qwen3.8:latest`) |
| `POSTGRES_*` | No | DB config (defaults: localhost/5432/face_recognition/postgres/postgres) |

## Docs

Detailed documentation in [`Backend/docs/`](Backend/docs/):
[API Reference](Backend/docs/API_README.md) · [Architecture](Backend/docs/API_ARCHITECTURE.md) · [Pipeline Flow](Backend/docs/PIPELINE_FLOW.md) · [Vision Analysis](Backend/docs/VISION_ANALYSIS_GUIDE.md) · [Shopping](Backend/docs/UNIFIED_SHOPPING_GUIDE.md) · [Deployment](Backend/docs/DEPLOYMENT.md) · [Setup](Backend/docs/UPDATED_PIPELINE_SETUP.md)
