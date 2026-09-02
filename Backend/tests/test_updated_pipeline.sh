#!/bin/bash
# Test script for updated_agentic_pipeline.py
# Verifies all dependencies and configuration

set -e

echo "=================================="
echo "Updated Pipeline Setup Verification"
echo "=================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
ALL_GOOD=true

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        ALL_GOOD=false
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python package '$1' is installed"
        return 0
    else
        echo -e "${RED}✗${NC} Python package '$1' is NOT installed"
        ALL_GOOD=false
        return 1
    fi
}

# Function to check environment variable
check_env_var() {
    if [ -n "${!1}" ]; then
        echo -e "${GREEN}✓${NC} Environment variable $1 is set"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Environment variable $1 is NOT set"
        return 1
    fi
}

echo "1. Checking System Dependencies"
echo "--------------------------------"
check_command python3
check_command psql
echo ""

echo "2. Checking PostgreSQL Service"
echo "--------------------------------"
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running"
else
    echo -e "${RED}✗${NC} PostgreSQL is NOT running"
    echo "   Start with: brew services start postgresql@15"
    ALL_GOOD=false
fi
echo ""

echo "3. Checking Database"
echo "--------------------------------"
DB_NAME="${POSTGRES_DB:-face_recognition}"
if psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo -e "${GREEN}✓${NC} Database '$DB_NAME' exists"
else
    echo -e "${YELLOW}⚠${NC} Database '$DB_NAME' does NOT exist"
    echo "   Create with: createdb $DB_NAME"
fi
echo ""

echo "4. Checking Python Packages"
echo "--------------------------------"
check_python_package "cv2"
check_python_package "numpy"
check_python_package "ultralytics"
check_python_package "requests"
check_python_package "psycopg2"
check_python_package "insightface"
check_python_package "onnxruntime"
echo ""

echo "5. Checking Environment Variables"
echo "--------------------------------"
if check_env_var "TMDB_API_KEY"; then
    # Validate API key format (should be 32 chars alphanumeric)
    if [[ ${TMDB_API_KEY} =~ ^[a-zA-Z0-9]{32}$ ]]; then
        echo "   API key format looks valid"
    else
        echo -e "   ${YELLOW}⚠${NC} API key format may be invalid (should be 32 alphanumeric chars)"
    fi
else
    echo "   Get API key at: https://www.themoviedb.org/settings/api"
    echo "   Set with: export TMDB_API_KEY=your_key_here"
    ALL_GOOD=false
fi

check_env_var "POSTGRES_HOST" || echo "   Using default: localhost"
check_env_var "POSTGRES_PORT" || echo "   Using default: 5432"
check_env_var "POSTGRES_DB" || echo "   Using default: face_recognition"
check_env_var "POSTGRES_USER" || echo "   Using default: postgres"
check_env_var "POSTGRES_PASSWORD" || echo "   Using default: postgres"
echo ""

echo "6. Checking YOLO Model"
echo "--------------------------------"
if [ -f "yolov8n.pt" ]; then
    echo -e "${GREEN}✓${NC} YOLO model (yolov8n.pt) exists"
else
    echo -e "${YELLOW}⚠${NC} YOLO model (yolov8n.pt) NOT found"
    echo "   It will be downloaded automatically on first run"
fi
echo ""

echo "7. Testing TMDB API Connection"
echo "--------------------------------"
if [ -n "$TMDB_API_KEY" ]; then
    RESPONSE=$(curl -s "https://api.themoviedb.org/3/search/movie?api_key=$TMDB_API_KEY&query=Inception" 2>/dev/null)
    if echo "$RESPONSE" | grep -q "\"success\":false"; then
        echo -e "${RED}✗${NC} TMDB API key is invalid"
        ALL_GOOD=false
    elif echo "$RESPONSE" | grep -q "\"total_results\""; then
        echo -e "${GREEN}✓${NC} TMDB API connection successful"
    else
        echo -e "${YELLOW}⚠${NC} Could not verify TMDB API connection"
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping (no API key set)"
fi
echo ""

echo "8. Testing Database Connection"
echo "--------------------------------"
if command -v psql &> /dev/null && pg_isready -q 2>/dev/null; then
    DB_HOST="${POSTGRES_HOST:-localhost}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_NAME="${POSTGRES_DB:-face_recognition}"
    DB_USER="${POSTGRES_USER:-postgres}"
    
    if PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Database connection successful"
        
        # Check for pgvector extension
        if PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT * FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q "vector"; then
            echo -e "${GREEN}✓${NC} pgvector extension is installed"
        else
            echo -e "${YELLOW}⚠${NC} pgvector extension is NOT installed"
            echo "   Install with: brew install pgvector"
            echo "   Then in psql: CREATE EXTENSION vector;"
        fi
    else
        echo -e "${RED}✗${NC} Database connection failed"
        echo "   Check your database credentials"
        ALL_GOOD=false
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping (PostgreSQL not available)"
fi
echo ""

echo "=================================="
echo "Summary"
echo "=================================="
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to use the updated pipeline:"
    echo "  python3 updated_agentic_pipeline.py input/image.jpg --movie \"Movie Title\""
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Please fix the issues above before running the pipeline."
    echo "See UPDATED_PIPELINE_SETUP.md for detailed setup instructions."
    exit 1
fi
