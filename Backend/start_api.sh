#!/bin/bash

# Quick start script for Agentic Pipeline API

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              AGENTIC PIPELINE API - QUICK START                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo ""
    echo "Please create .env file with:"
    echo "  TMDB_API_KEY=your_key_here"
    echo "  IMGBB_API_KEY=your_key_here"
    echo ""
    echo "Get API keys:"
    echo "  • TMDB: https://www.themoviedb.org/settings/api"
    echo "  • ImgBB: https://api.imgbb.com/"
    echo ""
    exit 1
fi

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL..."
if command -v docker &> /dev/null && docker ps | grep -q postgres; then
    echo "✓ PostgreSQL is running (Docker)"
elif command -v pg_isready &> /dev/null && pg_isready -q; then
    echo "✓ PostgreSQL is running (Local)"
else
    echo "⚠️  PostgreSQL not detected"
    echo ""
    echo "Start PostgreSQL with Docker:"
    echo "  docker-compose up -d"
    echo ""
    echo "Or install locally (see docs/UPDATED_PIPELINE_SETUP.md)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if dependencies are installed
echo ""
echo "🔍 Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  FastAPI not installed"
    echo ""
    echo "Install dependencies:"
    echo "  pip install -r requirements_api.txt"
    echo ""
    read -p "Install now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -r requirements_api.txt
    else
        exit 1
    fi
else
    echo "✓ Dependencies installed"
fi

# Start the API server
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                      STARTING API SERVER                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "API will be available at:"
echo "  • Main: http://localhost:8000"
echo "  • Docs: http://localhost:8000/docs"
echo "  • Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo ""

# Run the server
python3 api.py
