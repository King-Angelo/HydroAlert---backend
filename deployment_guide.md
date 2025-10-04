# HydroAlert Backend - Deployment & Operations Guide

## Table of Contents
1. [Project Overview & Quick Start](#1-project-overview--quick-start)
2. [Production Deployment (Containerized)](#2-production-deployment-containerized)
3. [Monitoring and Logging (Operational Readiness)](#3-monitoring-and-logging-operational-readiness)
4. [Maintenance and Scaling Considerations](#4-maintenance-and-scaling-considerations)

---

## 1. Project Overview & Quick Start

### Purpose
HydroAlert is a real-time flood monitoring system that provides:
- **IoT Sensor Data Ingestion**: Secure collection of water level, rainfall, and device health data
- **Emergency Report Management**: Community-submitted flood reports with triage workflow
- **Real-time Alerts**: WebSocket-based notifications for critical flood conditions
- **Geospatial Analysis**: PostGIS-powered location-based queries and proximity searches
- **Administrative Dashboard**: Complete sensor and report management interface

### Technology Stack
- **Backend Framework**: FastAPI 0.104+ (Python 3.12+)
- **Database**: PostgreSQL 17+ with PostGIS extension
- **Real-time Communication**: WebSockets with JWT authentication
- **File Storage**: Google Cloud Storage (configurable to local storage)
- **Authentication**: JWT tokens + HMAC signatures for IoT devices
- **Rate Limiting**: In-memory rate limiting with configurable policies
- **Logging**: Structured JSON logging with Loguru

### Minimum Required Environment Variables

Create a `.env` file with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/hydroalert

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
APP_NAME=HydroAlert Backend
DEBUG=false

# WebSocket Configuration
WEBSOCKET_CORS_ORIGINS=["https://yourdomain.com", "https://admin.yourdomain.com"]

# File Upload Configuration
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_FILE_TYPES=["image/jpeg", "image/png", "image/webp", "image/gif"]
MAX_FILES_PER_REPORT=5

# Cloud Storage Configuration (Google Cloud Storage)
CLOUD_STORAGE_ENABLED=true
CLOUD_STORAGE_BUCKET=hydroalert-evidence-prod
CLOUD_STORAGE_PUBLIC_URL=https://storage.googleapis.com/hydroalert-evidence-prod
CLOUD_STORAGE_CREDENTIALS_PATH=/path/to/service-account.json
CLOUD_STORAGE_MAKE_PUBLIC=false

# PostGIS Configuration
POSTGIS_ENABLED=true

# Security Configuration
BCRYPT_ROUNDS=12

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
LOG_CONSOLE_ENABLED=true
```

### Quick Start (Development)
```bash
# 1. Clone and setup
git clone <repository-url>
cd HydroAlert/Backend
python -m venv .venv312
.venv312\Scripts\activate  # Windows
# source .venv312/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup database
createdb hydroalert
# Install PostGIS extension (see Database Setup section)

# 4. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 5. Run application
python main.py
```

---

## 2. Production Deployment (Containerized)

### Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:17-3.4
    environment:
      POSTGRES_DB: hydroalert
      POSTGRES_USER: hydroalert_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hydroalert_user -d hydroalert"]
      interval: 10s
      timeout: 5s
      retries: 5

  hydroalert-backend:
    build: .
    environment:
      - DATABASE_URL=postgresql+asyncpg://hydroalert_user:${POSTGRES_PASSWORD}@postgres:5432/hydroalert
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CLOUD_STORAGE_ENABLED=${CLOUD_STORAGE_ENABLED}
      - CLOUD_STORAGE_BUCKET=${CLOUD_STORAGE_BUCKET}
      - CLOUD_STORAGE_CREDENTIALS_PATH=/app/credentials/service-account.json
    volumes:
      - ./uploads:/app/uploads
      - ./credentials:/app/credentials:ro
      - ./logs:/app/logs
    ports:
      - "8002:8002"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - hydroalert-backend
    restart: unless-stopped

volumes:
  postgres_data:
```

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["python", "main.py"]
```

### Database Migration Setup

Create `init-scripts/01-init-db.sql`:

```sql
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create application user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hydroalert_user') THEN
        CREATE ROLE hydroalert_user WITH LOGIN PASSWORD 'your_password_here';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE hydroalert TO hydroalert_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO hydroalert_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hydroalert_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hydroalert_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO hydroalert_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO hydroalert_user;
```

### Deployment Commands

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env with production values

# 2. Build and start services
docker-compose up -d --build

# 3. Check service health
docker-compose ps
docker-compose logs hydroalert-backend

# 4. Verify database connection
docker-compose exec hydroalert-backend python -c "
from app.database import get_session
import asyncio
async def test():
    async for session in get_session():
        print('Database connection successful')
        break
asyncio.run(test())
"

# 5. Run initial data setup (if needed)
docker-compose exec hydroalert-backend python -c "
from app.database import create_tables
import asyncio
asyncio.run(create_tables())
print('Database tables created successfully')
"
```

### SSL/TLS Configuration (Nginx)

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream hydroalert_backend {
        server hydroalert-backend:8002;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=websocket:10m rate=5r/s;

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://hydroalert_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket endpoints
        location /ws/ {
            limit_req zone=websocket burst=10 nodelay;
            proxy_pass http://hydroalert_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health {
            proxy_pass http://hydroalert_backend;
            access_log off;
        }
    }
}
```

---

## 3. Monitoring and Logging (Operational Readiness)

### Structured Logging Configuration

The system uses Loguru for structured JSON logging. All logs are written in JSON format for easy parsing and analysis.

#### Log Levels and Categories

```python
# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Structured fields: timestamp, level, logger, message, module, function, line, taskName
```

#### Key Log Patterns for Troubleshooting

### Security Events Monitoring

Filter logs for authentication and security issues:

```bash
# Monitor login failures and token issues
grep -E '"level":"WARNING".*"module":"auth"' /app/logs/hydroalert.log | jq '.'

# Monitor HMAC authentication failures
grep -E '"level":"WARNING".*"Authentication failed for sensor"' /app/logs/hydroalert.log | jq '.'

# Monitor rate limiting events
grep -E '"level":"WARNING".*"Rate limit exceeded"' /app/logs/hydroalert.log | jq '.'
```

**Example Security Log Entry:**
```json
{
  "timestamp": "2025-10-04T08:21:58.244542Z",
  "level": "WARNING",
  "logger": "app.routers.mobile.sensor_readings",
  "message": "Authentication failed for sensor SENSOR_001",
  "module": "sensor_readings",
  "function": "ingest_sensor_data",
  "line": 64
}
```

### Triage Workflow Monitoring

Track administrative actions and report processing:

```bash
# Monitor report triage events
grep -E '"level":"INFO".*"Report.*triaged"' /app/logs/hydroalert.log | jq '.'

# Monitor triage time metrics
grep -E '"level":"INFO".*"triage_time"' /app/logs/hydroalert.log | jq '.'

# Monitor report status changes
grep -E '"level":"INFO".*"status.*updated"' /app/logs/hydroalert.log | jq '.'
```

**Example Triage Log Entry:**
```json
{
  "timestamp": "2025-10-04T08:21:58.244542Z",
  "level": "INFO",
  "logger": "app.services.report_service",
  "message": "Report 123 triaged by admin_user: APPROVED",
  "module": "report_service",
  "function": "triage_report",
  "line": 45,
  "report_id": 123,
  "triaged_by": "admin_user",
  "new_status": "APPROVED",
  "triage_time_seconds": 180
}
```

### IoT Data Ingestion Monitoring

Debug sensor data processing and field mapping issues:

```bash
# Monitor successful data ingestion
grep -E '"level":"INFO".*"data ingested successfully"' /app/logs/hydroalert.log | jq '.'

# Monitor sensor health updates
grep -E '"level":"INFO".*"sensor.*health reported"' /app/logs/hydroalert.log | jq '.'

# Monitor field mapping errors
grep -E '"level":"ERROR".*"field mapping"' /app/logs/hydroalert.log | jq '.'

# Monitor HMAC signature errors
grep -E '"level":"ERROR".*"HMAC.*verification"' /app/logs/hydroalert.log | jq '.'
```

**Example IoT Ingestion Log Entry:**
```json
{
  "timestamp": "2025-10-04T08:21:58.261101Z",
  "level": "INFO",
  "logger": "app.routers.mobile.sensor_readings",
  "message": "Sensor SENSOR_001 data ingested successfully: water_level=45.5cm, rainfall=12.3mm, risk_level=LOW, battery=85%, signal=92%",
  "module": "sensor_readings",
  "function": "ingest_sensor_data",
  "line": 118,
  "sensor_id": "SENSOR_001",
  "water_level_cm": 45.5,
  "rainfall_mm": 12.3,
  "risk_level": "LOW",
  "battery_level": 85,
  "signal_strength": 92
}
```

### Performance Monitoring

Monitor API latency and system performance:

```bash
# Monitor API response times
grep -E '"level":"INFO".*"API.*latency"' /app/logs/hydroalert.log | jq '.'

# Monitor WebSocket connection events
grep -E '"level":"INFO".*"WebSocket.*connection"' /app/logs/hydroalert.log | jq '.'

# Monitor database query performance
grep -E '"level":"WARNING".*"slow.*query"' /app/logs/hydroalert.log | jq '.'
```

### Log Rotation and Retention

Configure log rotation in production:

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/hydroalert << EOF
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 hydroalert hydroalert
    postrotate
        docker-compose restart hydroalert-backend
    endscript
}
EOF
```

### Monitoring Dashboard Setup

For production monitoring, consider integrating with:

- **Prometheus + Grafana**: For metrics collection and visualization
- **ELK Stack**: For log aggregation and analysis
- **Sentry**: For error tracking and alerting

---

## 4. Maintenance and Scaling Considerations

### Database Maintenance

#### PostGIS Optimization

```sql
-- Check PostGIS version and extensions
SELECT PostGIS_Version();

-- Analyze and update table statistics
ANALYZE;

-- Check spatial indexes
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE indexdef LIKE '%gist%' OR indexdef LIKE '%geometry%';

-- Rebuild spatial indexes if needed
REINDEX INDEX CONCURRENTLY idx_flood_reading_location_geom;
REINDEX INDEX CONCURRENTLY idx_emergency_report_location_geom;
REINDEX INDEX CONCURRENTLY idx_sensor_location_geom;
```

#### Database Performance Monitoring

```sql
-- Monitor slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor connection usage
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';
```

#### Regular Maintenance Tasks

```bash
# Weekly maintenance script
#!/bin/bash
# maintenance.sh

echo "Starting weekly maintenance..."

# 1. Database vacuum and analyze
docker-compose exec postgres psql -U hydroalert_user -d hydroalert -c "VACUUM ANALYZE;"

# 2. Check for orphaned files in uploads
find /app/uploads -type f -mtime +30 -exec rm {} \;

# 3. Rotate logs
logrotate -f /etc/logrotate.d/hydroalert

# 4. Health check
curl -f http://localhost:8002/health || exit 1

echo "Maintenance completed successfully"
```

### WebSocket Server Scaling

#### Stateful Connection Considerations

The WebSocket server maintains stateful connections and requires special scaling considerations:

**Current Architecture:**
- In-memory connection management
- Real-time message broadcasting
- JWT-based authentication per connection

#### Horizontal Scaling Strategy

**Option 1: Load Balancer with Sticky Sessions**
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  hydroalert-backend:
    deploy:
      replicas: 3
    environment:
      - INSTANCE_ID=${HOSTNAME}
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  nginx:
    # Configure sticky sessions
    volumes:
      - ./nginx-sticky.conf:/etc/nginx/nginx.conf:ro
```

**Option 2: Redis-based Connection Management**

For true horizontal scaling, implement Redis-based connection management:

```python
# app/websocket/redis_connection_manager.py
import redis
import json
from typing import Dict, List

class RedisConnectionManager:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        self.local_connections: Dict[str, WebSocket] = {}
    
    async def add_connection(self, connection_id: str, websocket: WebSocket, user_data: dict):
        # Store locally
        self.local_connections[connection_id] = websocket
        
        # Store in Redis for cross-instance communication
        await self.redis_client.hset(
            "connections", 
            connection_id, 
            json.dumps({
                "instance_id": os.getenv("INSTANCE_ID"),
                "user_data": user_data
            })
        )
    
    async def broadcast_to_all(self, message: dict):
        # Broadcast to local connections
        for connection_id, websocket in self.local_connections.items():
            await websocket.send_json(message)
        
        # Publish to Redis for other instances
        await self.redis_client.publish("broadcast", json.dumps(message))
```

#### Load Balancer Configuration for WebSockets

```nginx
# nginx-sticky.conf
upstream hydroalert_backend {
    ip_hash;  # Sticky sessions based on IP
    server hydroalert-backend_1:8002;
    server hydroalert-backend_2:8002;
    server hydroalert-backend_3:8002;
}

server {
    location /ws/ {
        proxy_pass http://hydroalert_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific timeouts
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

### Backup and Recovery

#### Database Backup Strategy

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="hydroalert_backup_${DATE}.sql"

# Create backup
docker-compose exec postgres pg_dump -U hydroalert_user -d hydroalert > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to cloud storage (optional)
# gsutil cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" gs://hydroalert-backups/

# Cleanup old backups (keep 30 days)
find ${BACKUP_DIR} -name "hydroalert_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

#### File Storage Backup

```bash
#!/bin/bash
# backup-files.sh

# Backup local uploads
tar -czf "/backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz" /app/uploads

# Sync with cloud storage
gsutil rsync -r /app/uploads gs://hydroalert-evidence-backup/
```

### Disaster Recovery Plan

#### Recovery Procedures

1. **Database Recovery:**
```bash
# Restore from backup
docker-compose exec postgres psql -U hydroalert_user -d hydroalert < backup_file.sql
```

2. **Application Recovery:**
```bash
# Redeploy from source
git pull origin main
docker-compose up -d --build
```

3. **File Recovery:**
```bash
# Restore from cloud storage
gsutil rsync -r gs://hydroalert-evidence-backup/ /app/uploads
```

### Performance Tuning

#### Database Optimization

```sql
-- Optimize PostGIS queries
SET work_mem = '256MB';
SET shared_buffers = '1GB';
SET effective_cache_size = '4GB';

-- Create additional indexes for common queries
CREATE INDEX CONCURRENTLY idx_flood_reading_timestamp_risk 
ON floodreading (timestamp DESC, risk_level) 
WHERE risk_level IN ('HIGH', 'CRITICAL');

CREATE INDEX CONCURRENTLY idx_emergency_report_status_submitted 
ON emergencyreport (status, submitted_at DESC) 
WHERE status = 'PENDING';
```

#### Application Optimization

```python
# app/core/config.py - Production settings
class Settings(BaseSettings):
    # Database connection pooling
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 100
    
    # File upload optimization
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_chunk_size: int = 8192
```

### Security Hardening

#### Production Security Checklist

- [ ] Change default JWT secret key
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure firewall rules (only ports 80, 443, 22)
- [ ] Set up fail2ban for brute force protection
- [ ] Enable database SSL connections
- [ ] Configure proper CORS origins
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Backup encryption
- [ ] Access logging and audit trails

---

## Conclusion

This deployment guide provides comprehensive instructions for deploying, monitoring, and maintaining the HydroAlert backend system in production. The system is designed to be scalable, maintainable, and operationally ready for real-world flood monitoring applications.

For additional support or questions, refer to the application logs and monitoring systems configured in this guide.

**System Status: Production Ready ✅**
