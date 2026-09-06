# CineLens AI

AI-powered movie scene analysis — identify actors, detect objects, analyze scenes, and find shopping links from a single movie frame.

[![Demo](https://img.shields.io/badge/YouTube-Demo-red?logo=youtube)](https://youtu.be/hdk6e16dqUo)

## Highlights

- **Situation:** Movie and entertainment platforms need to extract structured metadata from video frames — who's on screen, what they're wearing, what objects are visible — but manual tagging doesn't scale and generic vision APIs lack movie-specific context.

- **Task:** Build an end-to-end system that takes a movie frame + movie name, identifies the specific actors from that film's cast, describes the scene in detail, and connects detected items to purchasable products — all with real-time progress feedback.

- **Action:** Combined YOLOv8 object detection with InsightFace face recognition and pgvector similarity search against TMDB cast embeddings. Added an optional local vision LLM (Ollama) for scene/clothing/object analysis with scene-context injection to correct YOLO misclassifications. Built a Redis job queue + worker architecture so FastAPI acts as a thin gateway while a separate worker handles ML inference, with SSE streaming progress through to the browser. Parallelized scene analysis with cast lookup and detection to reduce wall time.

- **Result:** Actors identified at 74–95% confidence in under 10 seconds (face matching only). Full vision analysis in 2–8 minutes on local hardware with 10-15s saved via parallel scene analysis. Redis-backed result caching returns identical requests instantly (24h TTL). Shopping recommendations via SerpAPI Google Shopping. Live progress UI with 9 streaming steps instead of a blank loading screen. Full observability via Grafana + Loki — every job traceable by ID through the entire pipeline with structured JSON logs.

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
│  • Checks Redis cache (movie_name + image_url hash)                  │
│  • Cache hit → instant SSE response (no worker needed)               │
│  • Cache miss → enqueues job to Redis                                │
│  • Subscribes to Redis pub/sub, streams progress as SSE              │
│  (No ML work — just message passing + caching)                       │
└──────────────────┬──────────────────────────▲────────────────────────┘
                   │ enqueue                  │ pub/sub
                   ▼                          │
┌──────────────────────────────────────────────────────────────────────┐
│  Redis (:6379)                                                       │
│  • Job queue (BLPOP)  • Result cache (24h TTL)  • Pub/sub channels  │
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

### Observability Stack

```
cinelens-api  ─┐                 ┌─► Loki (:3100) ──► Grafana (:3001)
               ├─ stdout (JSON) ─┤                    (dashboards, alerts)
cinelens-worker┘                 └─ Promtail
                                    (scrapes Docker logs, extracts job_id/level/step)
```

## Key Design Decisions

**Redis worker separation** — FastAPI doesn't run any ML inference. It enqueues jobs and proxies progress events. The worker process handles the heavy lifting. Multiple requests queue up without blocking the web server.

**Result caching** — Every completed analysis is cached in Redis under a deterministic key (`sha256(movie_name + image_url)`, 24h TTL). Identical requests return instantly from cache without touching the worker, YOLO, Ollama, or any external API. No client-side localStorage needed.

**SSE streaming** — Server-Sent Events from worker → Redis pub/sub → FastAPI → Next.js → browser. The UI shows 9 live progress steps instead of a blank screen for 8 minutes. Cache hits skip directly to the complete event.

**Parallel scene analysis** — Scene analysis (Ollama, 30-60s) starts immediately after image download and runs in a background thread while TMDB lookup, YOLO detection, and face matching happen on the main thread. Saves 10-15s of wall time.

**Scene-context injection** — YOLO only knows 80 COCO classes and often misclassifies objects (gun → cell phone, armor → vehicle). The scene analysis result is injected into each object's vision prompt so the LLM can override YOLO's label.

**Post-vision reclassification** — After the vision model describes each object, a keyword check moves misclassified items to the correct UI category (e.g. "Iron Man Armored Suit" moves from Vehicles to Other Objects).

**Structured observability** — Every Python module emits JSON logs to stdout with `job_id` context propagation via `ContextVar`. Promtail scrapes Docker container logs and pushes to Loki with `job_id`, `level`, `step` as indexed labels. Grafana provides a pre-provisioned dashboard with job dropdown and error panel. Zero new Python dependencies — uses stdlib `logging` + `json`.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, Tailwind CSS, SSE streaming |
| API Gateway | FastAPI, Uvicorn |
| Job Queue + Cache | Redis (pub/sub, BLPOP queue, result cache) |
| Object Detection | YOLOv8 |
| Face Recognition | InsightFace (512-dim embeddings) |
| Vector Search | PostgreSQL + pgvector (HNSW index) |
| Cast Data | TMDB API |
| Vision Analysis | Ollama (local LLM) |
| Image Hosting | ImgBB |
| Shopping | SerpAPI Google Shopping |
| Observability | Grafana + Loki + Promtail (structured JSON logs) |

## Project Structure

```
├── docker-compose.yml               All services (postgres, redis, api, worker, frontend, loki, promtail, grafana)
├── Frontend/
│   ├── Dockerfile
│   ├── app/page.tsx                  Main page (SSE progress + job_id display + results)
│   ├── app/api/analyze-movie/        API route (ImgBB upload + SSE proxy)
│   ├── components/input-panel.tsx    Movie name + image input
│   └── components/output-panel.tsx   Results display (with job_id in header)
│
├── Backend/
│   ├── Dockerfile
│   ├── api.py                        FastAPI gateway (enqueue + SSE proxy)
│   ├── worker.py                     ML pipeline worker (Redis consumer)
│   ├── logging_config.py             Structured JSON logging (job_id context propagation)
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
│
├── observability/
│   ├── promtail.yml                  Log collector config (scrapes Docker container logs)
│   └── grafana/
│       └── provisioning/
│           ├── datasources/loki.yml  Loki datasource auto-config
│           └── dashboards/
│               ├── default.yml       Dashboard provider config
│               └── json/
│                   └── cinelens-jobs.json  Pre-built job log dashboard
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
docker compose up -d --build
# Ollama runs on host: ollama pull qwen3.8:latest
```

Services after startup:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/docs
- **Grafana:** http://localhost:3001 (admin/admin)

### Common Docker commands

```bash
docker compose up -d --build api worker   # rebuild after Python code changes
docker compose up -d api worker           # restart after .env changes (no rebuild)
docker compose up -d --build frontend     # rebuild after frontend code or env changes
docker compose restart promtail           # reload promtail.yml config
docker compose down                       # stop everything (volumes preserved)
docker compose down -v                    # stop + delete all data (volumes removed)
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

## Observability

Every API call, pipeline step, and external service call is logged as structured JSON with `job_id` context — searchable in Grafana.

**Access:** http://localhost:3001 (admin/admin) → Dashboards → CineLens Job Logs

**What you see:**
- Job ID dropdown auto-populated with recent jobs
- Full pipeline timeline per job: download → init → cast → detect → identify → scene → objects → upload
- Face match scores and actor names
- TMDB/Ollama/ImgBB API call results and failures
- Error panel with stack traces across all jobs
- Log volume chart by container

**How it works:**

```
Python logger → JSON to stdout → Docker captures → Promtail scrapes → Loki stores → Grafana queries
```

All Python modules use `logging_config.get_logger()` which emits one JSON object per line with `ts`, `level`, `job_id`, `step`, `msg`, and contextual fields (`actor`, `movie`, `error`, `count`, `duration`). Promtail extracts `job_id`, `level`, and `step` as Loki labels for fast filtering.

The frontend also displays the current `job_id` during processing and in the results header — copy it into Grafana to inspect what happened.

**Useful LogQL queries** (Grafana → Explore → Loki):

```
{container="cinelens-worker"} | json | level = `ERROR`        # all errors
{container="cinelens-worker"} | json | step = `identify`       # face recognition results
{container="cinelens-worker"} | json | step = `tmdb`           # TMDB API calls
{container=~"cinelens-.*"} |= `some_job_id` | json            # everything for one job
```

## Docs

Detailed documentation in [`Backend/docs/`](Backend/docs/):
[API Reference](Backend/docs/API_README.md) · [Architecture](Backend/docs/API_ARCHITECTURE.md) · [Pipeline Flow](Backend/docs/PIPELINE_FLOW.md) · [Vision Analysis](Backend/docs/VISION_ANALYSIS_GUIDE.md) · [Shopping](Backend/docs/UNIFIED_SHOPPING_GUIDE.md) · [Deployment](Backend/docs/DEPLOYMENT.md) · [Setup](Backend/docs/UPDATED_PIPELINE_SETUP.md)
