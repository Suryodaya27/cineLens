# CineLens AI

AI-powered movie scene analysis — identify actors, detect objects, analyze scenes, and find shopping links from a single movie frame.

## Highlights

- **Situation:** Movie and entertainment platforms need to extract structured metadata from video frames — who's on screen, what they're wearing, what objects are visible — but manual tagging doesn't scale and generic vision APIs lack movie-specific context.

- **Task:** Build an end-to-end system that takes a movie frame + movie name, identifies the specific actors from that film's cast, describes the scene in detail, and connects detected items to purchasable products — all with real-time progress feedback.

- **Action:** Combined YOLOv8 object detection with InsightFace face recognition and pgvector similarity search against TMDB cast embeddings. Added an optional local vision LLM (Ollama) for scene/clothing/object analysis with scene-context injection to correct YOLO misclassifications. Built a Redis job queue + worker architecture so FastAPI acts as a thin gateway while a separate worker handles ML inference, with SSE streaming progress through to the browser. Parallelized scene analysis with cast lookup and detection to reduce wall time.

- **Result:** Actors identified at 74–95% confidence in under 10 seconds (face matching only). Full vision analysis in 2–8 minutes on local hardware with 10-15s saved via parallel scene analysis. Shopping recommendations via SerpAPI Google Shopping. Live progress UI with 9 streaming steps instead of a blank loading screen.

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
│  FastAPI API Gateway (localhost:8000)                                 │
│                                                                      │
│  • Validates request                                                 │
│  • Enqueues job to Redis                                             │
│  • Subscribes to Redis pub/sub                                       │
│  • Streams progress events as SSE                                    │
│  (No ML work — just message passing)                                 │
└──────────────────┬──────────────────────────▲────────────────────────┘
                   │ enqueue                  │ pub/sub
                   ▼                          │
┌──────────────────────────────────────────────────────────────────────┐
│  Redis (:6379)                                                       │
│  • Job queue (BLPOP)   • Job status/results   • Pub/sub channels    │
└──────────────────┬──────────────────────────▲────────────────────────┘
                   │ dequeue                  │ publish progress
                   ▼                          │
┌──────────────────────────────────────────────────────────────────────┐
│  Worker (python worker.py)                                           │
│                                                                      │
│  Main thread:              Background thread:                        │
│  1. Download image ──────► Scene analysis starts (Ollama)            │
│  2. Init YOLO+InsightFace   │ (runs while steps 3-5 use CPU)        │
│  3. TMDB cast lookup        │                                        │
│  4. YOLO detection          │                                        │
│  5. Face match (pgvector)   │                                        │
│  6. .join() ◄───────────────┘                                        │
│  7. Person/object vision analysis (with scene context)               │
│  8. Reclassify misdetected objects                                   │
│  9. Upload crops to ImgBB                                            │
│                                                                      │
│  Publishes progress events to Redis after each step                  │
└───────────┬──────────────────┬──────────────────┬────────────────────┘
            ▼                  ▼                  ▼
   PostgreSQL+pgvector     TMDB API         Ollama (local LLM)
   (face embeddings)    (cast, images)     (scene/object analysis)
```

## Key Design Decisions

**Redis worker separation** — FastAPI doesn't run any ML inference. It enqueues jobs and proxies progress events. The worker process handles the heavy lifting. Multiple requests queue up without blocking the web server.

**SSE streaming** — Server-Sent Events from worker → Redis pub/sub → FastAPI → Next.js → browser. The UI shows 9 live progress steps instead of a blank screen for 8 minutes.

**Parallel scene analysis** — Scene analysis (Ollama, 30-60s) starts immediately after image download and runs in a background thread while TMDB lookup, YOLO detection, and face matching happen on the main thread. Saves 10-15s of wall time.

**Scene-context injection** — YOLO only knows 80 COCO classes and often misclassifies objects (gun → cell phone, armor → vehicle). The scene analysis result is injected into each object's vision prompt so the LLM can override YOLO's label.

**Post-vision reclassification** — After the vision model describes each object, a keyword check moves misclassified items to the correct UI category (e.g. "Iron Man Armored Suit" moves from Vehicles to Other Objects).

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, Tailwind CSS, SSE streaming |
| API Gateway | FastAPI, Uvicorn |
| Job Queue | Redis (pub/sub + BLPOP queue) |
| Object Detection | YOLOv8 |
| Face Recognition | InsightFace (512-dim embeddings) |
| Vector Search | PostgreSQL + pgvector (HNSW index) |
| Cast Data | TMDB API |
| Vision Analysis | Ollama (local LLM) |
| Image Hosting | ImgBB |
| Shopping | SerpAPI Google Shopping |

## Project Structure

```
├── docker-compose.yml               All services (postgres, redis, api, worker, frontend)
├── Frontend/
│   ├── Dockerfile
│   ├── app/page.tsx                  Main page (SSE progress + results)
│   ├── app/api/analyze-movie/        API route (ImgBB upload + SSE proxy)
│   ├── components/input-panel.tsx    Movie name + image input
│   └── components/output-panel.tsx   Results display
│
├── Backend/
│   ├── Dockerfile
│   ├── api.py                        FastAPI gateway (enqueue + SSE proxy)
│   ├── worker.py                     ML pipeline worker (Redis consumer)
│   ├── pipelines/                    ML modules
│   │   └── updated_agentic_pipeline.py  YOLO + InsightFace + vision LLM
│   ├── services/                     Business logic
│   │   ├── unified_shopping.py       Shopping orchestrator
│   │   ├── amazon_shopping.py        SerpAPI Google Shopping
│   │   ├── visual_search.py          SerpAPI visual search
│   │   └── tmdb_enrichment.py        TMDB actor enrichment
│   ├── scripts/                      Debug utilities
│   ├── tests/                        Integration tests
│   └── docs/                         Detailed documentation
```

## Prerequisites

**Runtime:** Python 3.8+, Node.js 20+, Docker

**API keys (all free):**
- [TMDB](https://www.themoviedb.org/settings/api) — cast data and actor images (required)
- [ImgBB](https://api.imgbb.com/) — image hosting (required)
- [SerpAPI](https://serpapi.com/users/sign_up) — shopping search (optional, 250 free/month)

**Optional:** [Ollama](https://ollama.com) — only needed for vision analysis (`enable_vision=1`)

## Quick Start

### Option A: Docker Compose (everything)

```bash
cp Backend/.env.example Backend/.env   # fill in API keys
docker-compose up -d --build
# Ollama runs on host: ollama pull qwen3.8:latest
```

### Option B: Local development

```bash
# 1. Infrastructure
docker-compose up -d postgres redis

# 2. Backend API
cd Backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TMDB_API_KEY and IMGBB_API_KEY
python api.py           # → http://localhost:8000

# 3. Worker (separate terminal)
cd Backend && source .venv/bin/activate
python worker.py

# 4. Frontend (separate terminal)
cd Frontend && npm install
cp .env.example .env.local
npm run dev             # → http://localhost:3000

# 5. Vision model (optional)
ollama pull qwen3.8:latest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Analyze image (JSON response) |
| POST | `/analyze-stream` | Analyze image (SSE via Redis worker) |
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
| `SERPAPI_KEY` | No | Shopping search |
| `VISION_MODEL` | No | Ollama model (default: `qwen3.8:latest`) |
| `REDIS_URL` | No | Redis connection (default: `redis://localhost:6379/0`) |
| `POSTGRES_*` | No | DB config (defaults: localhost/5432/face_recognition/postgres/postgres) |

## Docs

Detailed documentation in [`Backend/docs/`](Backend/docs/):
[API Reference](Backend/docs/API_README.md) · [Architecture](Backend/docs/API_ARCHITECTURE.md) · [Pipeline Flow](Backend/docs/PIPELINE_FLOW.md) · [Vision Analysis](Backend/docs/VISION_ANALYSIS_GUIDE.md) · [Shopping](Backend/docs/UNIFIED_SHOPPING_GUIDE.md) · [Deployment](Backend/docs/DEPLOYMENT.md) · [Setup](Backend/docs/UPDATED_PIPELINE_SETUP.md)
