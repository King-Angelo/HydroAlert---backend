# HydroAlert Backend - Quick Reference

## 🚀 Quick Commands

### Development
```bash
# Start development server
python main.py

# Test IoT ingestion
python test_iot_ingestion_final.py

# Check health
curl http://localhost:8002/health
```

### Production
```bash
# Deploy with Docker
docker-compose up -d --build

# Check logs
docker-compose logs -f hydroalert-backend

# Database backup
docker-compose exec postgres pg_dump -U hydroalert_user -d hydroalert > backup.sql

# Scale WebSocket servers
docker-compose up -d --scale hydroalert-backend=3
```

## 🔍 Key Endpoints

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `POST /api/mobile/sensor-data/ingest` | IoT data ingestion | HMAC |
| `GET /api/mobile/sensor-data/health/{id}` | Sensor health check | HMAC |
| `GET /api/admin/sensors` | List all sensors | JWT Admin |
| `GET /api/admin/sensors/{id}/health` | Sensor health history | JWT Admin |
| `POST /api/admin/sensors/register` | Register new sensor | JWT Admin |
| `WS /ws/realtime` | Real-time updates | JWT |
| `WS /ws/map` | Map data stream | JWT |

## 📊 Monitoring Commands

```bash
# Security events
grep '"level":"WARNING".*"module":"auth"' /app/logs/hydroalert.log

# IoT ingestion
grep '"data ingested successfully"' /app/logs/hydroalert.log

# Triage workflow
grep '"Report.*triaged"' /app/logs/hydroalert.log

# Performance
grep '"API.*latency"' /app/logs/hydroalert.log
```

## 🛠️ Troubleshooting

### Common Issues
1. **PostGIS not available**: Install PostGIS extension in PostgreSQL
2. **HMAC auth fails**: Check sensor signature generation
3. **WebSocket disconnects**: Check JWT token expiration
4. **Rate limiting**: Adjust limits in config or check for abuse

### Health Checks
```bash
# Application health
curl http://localhost:8002/health

# Database connection
docker-compose exec hydroalert-backend python -c "from app.database import get_session; print('DB OK')"

# WebSocket connectivity
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8002/ws/realtime
```

## 📋 Environment Variables (Required)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/hydroalert
JWT_SECRET_KEY=your-secret-key-here
CLOUD_STORAGE_ENABLED=true
CLOUD_STORAGE_BUCKET=your-bucket-name
POSTGIS_ENABLED=true
```

## 🔧 Maintenance Schedule

- **Daily**: Check logs for errors
- **Weekly**: Database VACUUM ANALYZE
- **Monthly**: Security updates, backup verification
- **Quarterly**: Performance review, capacity planning
