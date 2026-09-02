# API Deployment Guide

Guide for deploying the Agentic Pipeline API to production.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Python 3.8+
- PostgreSQL 12+ with pgvector
- 4GB+ RAM
- 10GB+ disk space

## Production Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv git

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install pgvector
sudo apt install -y postgresql-server-dev-all
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. Application Setup

```bash
# Clone repository
git clone <your-repo-url>
cd <repo-directory>

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements_api.txt
pip install gunicorn
```

### 3. Database Setup

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE face_recognition;
CREATE USER api_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE face_recognition TO api_user;
\c face_recognition
CREATE EXTENSION vector;
EOF
```

### 4. Environment Configuration

Create `/etc/agentic-api/.env`:

```bash
# API Keys
TMDB_API_KEY=your_tmdb_api_key
IMGBB_API_KEY=your_imgbb_api_key

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=api_user
POSTGRES_PASSWORD=secure_password_here

# Optional: Vision model settings
# OLLAMA_HOST=http://localhost:11434
```

### 5. Systemd Service

Create `/etc/systemd/system/agentic-api.service`:

```ini
[Unit]
Description=Agentic Pipeline API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/agentic-pipeline
Environment="PATH=/opt/agentic-pipeline/venv/bin"
EnvironmentFile=/etc/agentic-api/.env
ExecStart=/opt/agentic-pipeline/venv/bin/gunicorn api:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile /var/log/agentic-api/access.log \
    --error-logfile /var/log/agentic-api/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create log directory:
```bash
sudo mkdir -p /var/log/agentic-api
sudo chown www-data:www-data /var/log/agentic-api
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agentic-api
sudo systemctl start agentic-api
sudo systemctl status agentic-api
```

### 6. Nginx Reverse Proxy

Install Nginx:
```bash
sudo apt install -y nginx
```

Create `/etc/nginx/sites-available/agentic-api`:

```nginx
upstream agentic_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://agentic_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://agentic_api/health;
        access_log off;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/agentic-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt
RUN pip install --no-cache-dir gunicorn

# Copy application
COPY . .

# Create temp directory
RUN mkdir -p temp_api_uploads

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "api:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300"]
```

### docker-compose.yml (Production)

```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: face_recognition
      POSTGRES_USER: api_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - api_network

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      TMDB_API_KEY: ${TMDB_API_KEY}
      IMGBB_API_KEY: ${IMGBB_API_KEY}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: face_recognition
      POSTGRES_USER: api_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    depends_on:
      - postgres
    restart: always
    networks:
      - api_network
    volumes:
      - ./cache:/app/cache
      - ./temp_api_uploads:/app/temp_api_uploads

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: always
    networks:
      - api_network

volumes:
  postgres_data:

networks:
  api_network:
    driver: bridge
```

Deploy:
```bash
docker-compose up -d
```

## Monitoring

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check service status
sudo systemctl status agentic-api

# View logs
sudo journalctl -u agentic-api -f
tail -f /var/log/agentic-api/error.log
```

### Performance Monitoring

Install monitoring tools:
```bash
pip install prometheus-fastapi-instrumentator
```

Add to `api.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

# After app creation
Instrumentator().instrument(app).expose(app)
```

Access metrics at: `http://your-domain.com/metrics`

## Security

### 1. API Key Authentication

Add authentication middleware to `api.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Add to endpoints
@app.post("/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_image(...):
    ...
```

### 2. Rate Limiting

```bash
pip install slowapi
```

Add to `api.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_image(request: Request, ...):
    ...
```

### 3. Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Scaling

### Horizontal Scaling

Use load balancer (e.g., Nginx, HAProxy) with multiple API instances:

```nginx
upstream agentic_api {
    least_conn;
    server api1.internal:8000;
    server api2.internal:8000;
    server api3.internal:8000;
}
```

### Database Optimization

```sql
-- Add indexes for faster queries
CREATE INDEX idx_actor_id ON face_embeddings(actor_id);
CREATE INDEX idx_created_at ON face_embeddings(created_at);

-- Vacuum regularly
VACUUM ANALYZE face_embeddings;
```

### Caching

Add Redis for caching results:

```bash
pip install redis
```

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache results
cache_key = f"analysis:{image_url}:{movie_name}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)

# Store result
redis_client.setex(cache_key, 3600, json.dumps(result))
```

## Backup

### Database Backup

```bash
# Create backup script
cat > /usr/local/bin/backup-agentic-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/agentic-api"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -U api_user face_recognition | gzip > $BACKUP_DIR/backup_$DATE.sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-agentic-db.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-agentic-db.sh" | sudo crontab -
```

## Troubleshooting

### High Memory Usage
- Reduce number of Gunicorn workers
- Enable swap if needed
- Monitor with `htop` or `free -h`

### Slow Processing
- Check database query performance
- Verify YOLO model size (use yolov8n for faster processing)
- Monitor with `top` or `htop`

### Database Connection Issues
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `.env`
- Check connection limits: `SHOW max_connections;`

### API Timeouts
- Increase timeout in Nginx and Gunicorn configs
- Use fast mode (enable_vision=0) for quicker responses
- Consider async processing for long-running tasks

## Support

For issues:
1. Check logs: `sudo journalctl -u agentic-api -f`
2. Review error logs: `/var/log/agentic-api/error.log`
3. Test health endpoint: `curl http://localhost:8000/health`
4. Verify database: `sudo -u postgres psql face_recognition`
