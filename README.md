# Auto Project Manager - Quick Start & Troubleshooting

## 🚀 Quick Start (5 minutes)

### Option 1: Using Docker (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-repo/auto_project_manager.git
cd auto_project_manager

# 2. Copy environment template
cp .env.example .env

# 3. Update .env with your Zalo credentials
nano .env
# Edit:
# - ZALO_ACCESS_TOKEN
# - ZALO_OA_ID

# 4. Start all services
docker-compose -f docker-compose-full.yml up -d

# 5. Verify services
docker-compose ps
curl http://localhost:8000/health

# 6. View API documentation
# Open: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup .env
cp .env.example .env
# Edit with your credentials

# 4. Initialize database
python -c "from database import init_db; init_db()"

# 5. Run all services (in separate terminals)

# Terminal 1: FastAPI Server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Assign Task Agent
cd agents
uvicorn assign_task_agent:app --reload --host 0.0.0.0 --port 8001

# Terminal 3: Exchange Task Agent
cd agents
uvicorn exchange_task_agent:app --reload --host 0.0.0.0 --port 8002

# 6. Test the API
curl http://localhost:8000/health
```

---

## 📋 Project Structure

```
auto_project_manager/
├── main.py                     # FastAPI entry point
├── database.py                 # SQLAlchemy setup
├── models.py                   # Database models
├── schemas.py                  # Pydantic schemas
├── requirements.txt            # Dependencies
├── .env.example               # Environment template
├── .env                       # (create this, never commit)
│
├── services/
│   ├── __init__.py
│   ├── project_service.py     # Project/Task/User management
│   ├── agent_service.py       # Agent communication
│   ├── zalo_service.py        # Zalo OA integration
│   └── notification_service.py
│
├── agents/
│   ├── __init__.py
│   ├── assign_task_agent.py   # Port 8001
│   └── exchange_task_agent.py # Port 8002
│
├── qrcodes/                    # Generated QR codes
├── logs/                       # Log files
│
├── Dockerfile                  # FastAPI container
├── Dockerfile.agent           # Agent container
├── docker-compose-full.yml    # Complete deployment
│
├── startup.sh                  # Startup script
├── stop.sh                     # Shutdown script
└── deploy.sh                   # Production deployment
```

---

## 🔧 Common Tasks

### Create a User

```bash
curl -X POST http://localhost:8000/api/users/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nguyễn Văn A",
    "email": "user@example.com",
    "phone": "+84912345678",
    "cv": "5 năm kinh nghiệm Python",
    "description": "Backend Developer",
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "role": "staff"
  }'
```

### Create a Project

```bash
curl -X POST http://localhost:8000/api/projects/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Website Redesign",
    "description": "Complete website redesign project",
    "manager_id": "user-id-from-previous-step"
  }'
```

### Create a Task

```bash
curl -X POST http://localhost:8000/api/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Design Homepage",
    "description": "Create mockups for homepage",
    "project_id": "project-id-from-previous-step",
    "priority": "high",
    "deadline": "2025-12-31T23:59:59",
    "requirements": ["Figma", "UI/UX"]
  }'
```

### Assign a Task

```bash
curl -X POST http://localhost:8000/api/assignments/assign \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-id",
    "task_id": "task-id"
  }'
```

---

## 🐛 Troubleshooting

### Issue: Port Already in Use

**Problem:** Error like "Address already in use" when starting services

**Solution:**
```bash
# Find process using port
lsof -i :8000  # For port 8000
# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn main:app --port 8001
```

---

### Issue: Database Connection Error

**Problem:** "could not connect to server: Connection refused"

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Or start PostgreSQL
sudo systemctl start postgresql

# For SQLite (development), ensure directory exists
mkdir -p /path/to/db
```

---

### Issue: Agent Timeout

**Problem:** Request to agent times out

**Solution:**
```bash
# 1. Check agent is running
curl http://localhost:8001/health
curl http://localhost:8002/health

# 2. Check logs
tail -f logs/AssignTaskAgent.log
tail -f logs/ExchangeTaskAgent.log

# 3. Increase timeout in .env
# Add: AGENT_TIMEOUT=60

# 4. In agent_service.py, update:
self.timeout = 60  # from 30
```

---

### Issue: Zalo Link Not Working

**Problem:** Zalo link/QR code returns 404 or invalid

**Solution:**
```bash
# 1. Verify Zalo credentials
echo $ZALO_OA_ID
echo $ZALO_ACCESS_TOKEN

# 2. Test Zalo API
curl -X GET https://openapi.zalo.me/v3/oa/getinfo \
  -H "Authorization: Bearer $ZALO_ACCESS_TOKEN"

# 3. If not working, regenerate token in Zalo dashboard:
# - Go to https://oa.zalo.me
# - Settings → API Settings
# - Generate new access token

# 4. Update .env
nano .env
# ZALO_ACCESS_TOKEN=new_token_here

# 5. Restart services
docker-compose restart
# or
pkill -f uvicorn && ./startup.sh
```

---

### Issue: QR Code Not Generated

**Problem:** QR code path returns null or file not found

**Solution:**
```bash
# 1. Ensure qrcodes directory exists
mkdir -p qrcodes
chmod 755 qrcodes

# 2. Check permissions
ls -la qrcodes/

# 3. Check logs for errors
tail -f logs/FastAPI.log | grep qrcode

# 4. Test QR generation manually
python << 'EOF'
import qrcode
from datetime import datetime

qr = qrcode.QRCode(version=1, box_size=10, border=4)
qr.add_data("https://example.com")
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save(f"qrcodes/test_{datetime.now().timestamp()}.png")
print("✓ QR code generated successfully")
EOF
```

---

### Issue: Database Migrations

**Problem:** Model changes not reflected in database

**Solution:**
```bash
# For development, delete and recreate:
rm auto_project_manager.db  # SQLite
python -c "from database import init_db; init_db()"

# For PostgreSQL, drop and recreate:
psql -U user -d postgres
DROP DATABASE auto_project_manager;
CREATE DATABASE auto_project_manager;
\q

# Then reinitialize
python -c "from database import init_db; init_db()"
```

---

### Issue: Agent Not Receiving Data

**Problem:** Agent endpoints return empty or error

**Solution:**
```bash
# 1. Check agent logs
docker logs auto_pm_assign_agent
docker logs auto_pm_exchange_agent

# 2. Test agent directly
curl -X POST http://localhost:8001/api/agents/assign-task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test",
    "title": "Test Task",
    "priority": "high",
    "requirements": ["Python"],
    "project_id": "test"
  }'

# 3. Check network connectivity between services
docker exec auto_pm_api ping assign_agent
docker exec auto_pm_api ping exchange_agent

# 4. Verify environment variables
docker exec auto_pm_api env | grep AGENT
```

---

### Issue: High Memory Usage

**Problem:** Docker containers consuming too much memory

**Solution:**
```yaml
# Update docker-compose.yml
services:
  fastapi:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

### Issue: Slow Response

**Problem:** API requests taking too long

**Solution:**
```bash
# 1. Check database performance
# Add connection pooling
ENGINE_KWARGS = {
    "pool_size": 20,
    "max_overflow": 40,
    "pool_pre_ping": True
}

# 2. Add caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user(user_id: str):
    # Cached result

# 3. Use async properly
async def slow_operation():
    # Your code here

# 4. Monitor with logs
import time
start = time.time()
# operation
duration = time.time() - start
logger.info(f"Operation took {duration}s")
```

---

## 📊 Monitoring

### Health Check Endpoints

```bash
# Main API
curl http://localhost:8000/health

# Agent 1
curl http://localhost:8001/health

# Agent 2
curl http://localhost:8002/health
```

### View Logs

```bash
# Docker
docker-compose logs -f fastapi
docker-compose logs -f assign_agent
docker-compose logs -f exchange_agent

# Local
tail -f logs/FastAPI.log
tail -f logs/AssignTaskAgent.log
tail -f logs/ExchangeTaskAgent.log

# Real-time
watch -n 1 'tail -5 logs/FastAPI.log'
```

### Database Queries

```bash
# Connect to PostgreSQL
psql -U user -d auto_project_manager

# Common queries
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM assignments WHERE status = 'pending';
SELECT * FROM assignments ORDER BY created_at DESC LIMIT 10;

# Analyze slow queries
EXPLAIN ANALYZE SELECT * FROM tasks WHERE priority = 'high';
```

---

## 🔒 Security Checklist

- [ ] Never commit .env file
- [ ] Use strong database password
- [ ] Rotate Zalo access token regularly
- [ ] Enable HTTPS in production
- [ ] Set up firewall rules
- [ ] Use environment-specific configs
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Validate all inputs
- [ ] Sanitize database queries
- [ ] Keep dependencies updated
- [ ] Review error logs for sensitive data

---

## 📈 Performance Optimization

### Database Optimization

```python
# Add indexes
class User(Base):
    email = Column(String(255), index=True)
    created_at = Column(DateTime, index=True)

# Connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

### API Optimization

```python
# Pagination
@app.get("/api/tasks/")
async def list_tasks(skip: int = 0, limit: int = 10):
    return db.query(Task).offset(skip).limit(limit).all()

# Caching
from fastapi_cache2 import FastAPICache2
@app.get("/api/projects/", cache=3600)
async def get_projects():
    # Results cached for 1 hour
```

### Docker Optimization

```dockerfile
# Use slim base image
FROM python:3.11-slim

# Multi-stage build
FROM python:3.11 as builder
# Build stage

FROM python:3.11-slim
# Final stage
COPY --from=builder /app /app
```

---

## 📞 Support & Resources

- **API Documentation:** http://localhost:8000/docs
- **GitHub:** https://github.com/your-repo
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **PostgreSQL Docs:** https://www.postgresql.org/docs
- **Docker Docs:** https://docs.docker.com
- **Zalo API Docs:** https://developers.zalo.me

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📝 License

MIT License - See LICENSE file for details