#!/bin/bash
# ============================================
# startup.sh - Script để khởi động toàn bộ hệ thống
# ============================================

set -e

echo "================================"
echo "Auto Project Manager - Startup"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# ============================================
# 1. Check Prerequisites
# ============================================
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    exit 1
fi
print_status "Python 3 found: $(python3 --version)"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    print_warning "PostgreSQL not found. Using SQLite for development."
    USE_SQLITE=true
else
    print_status "PostgreSQL found"
    USE_SQLITE=false
fi

# Check Docker (optional)
if command -v docker &> /dev/null; then
    print_status "Docker found: $(docker --version)"
else
    print_warning "Docker not found (optional)"
fi

# ============================================
# 2. Setup Virtual Environment
# ============================================
echo -e "\n${YELLOW}Setting up virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate || . venv/Scripts/activate
print_status "Virtual environment activated"

# ============================================
# 3. Install Dependencies
# ============================================
echo -e "\n${YELLOW}Installing dependencies...${NC}"

pip install --upgrade pip
pip install -r requirements.txt
print_status "Dependencies installed"

# ============================================
# 4. Setup Environment Variables
# ============================================
echo -e "\n${YELLOW}Setting up environment variables...${NC}"

if [ ! -f ".env" ]; then
    if [ ! -f ".env.example" ]; then
        print_warning "No .env.example found. Creating .env with defaults..."
        cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./auto_project_manager.db

# Server
SERVER_BASE_URL=http://localhost:8000

# Agent Services
ASSIGN_TASK_AGENT_URL=http://localhost:8001/api/agents/assign-task
EXCHANGE_TASK_AGENT_URL=http://localhost:8002/api/agents/exchange-task

# Zalo OA Configuration
ZALO_BASE_URL=https://openapi.zalo.me
ZALO_ACCESS_TOKEN=your_token_here
ZALO_OA_ID=your_oa_id_here
ZALO_SECRET_KEY=your_secret_here

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
    else
        cp .env.example .env
    fi
    print_status ".env file created. Please update with your credentials."
    echo -e "${YELLOW}Edit .env file with your configuration:${NC}"
    echo "  - ZALO_ACCESS_TOKEN"
    echo "  - ZALO_OA_ID"
    echo "  - Database connection if not using SQLite"
else
    print_status ".env file already exists"
fi

# ============================================
# 5. Initialize Database
# ============================================
echo -e "\n${YELLOW}Initializing database...${NC}"

python3 << 'PYEOF'
from database import init_db
try:
    init_db()
    print("✓ Database initialized")
except Exception as e:
    print(f"✗ Error initializing database: {e}")
    exit(1)
PYEOF

# ============================================
# 6. Start Services
# ============================================
echo -e "\n${YELLOW}Starting services...${NC}"

# Create logs directory
mkdir -p logs

# Function to run service in background
run_service() {
    local service_name=$1
    local port=$2
    local module=$3
    
    echo "Starting $service_name on port $port..."
    
    if [ "$service_name" = "FastAPI" ]; then
        nohup python -m uvicorn main:app --host 0.0.0.0 --port $port > logs/${service_name}.log 2>&1 &
    else
        nohup python -m uvicorn $module --host 0.0.0.0 --port $port > logs/${service_name}.log 2>&1 &
    fi
    
    echo $! > logs/${service_name}.pid
    sleep 2
    
    # Check if service started
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        print_status "$service_name is running on port $port"
    else
        print_warning "$service_name may not have started. Check logs/${service_name}.log"
    fi
}

# Start all services
run_service "FastAPI" 8000 "main:app"
run_service "AssignTaskAgent" 8001 "agents.assign_task_agent:app"
run_service "ExchangeTaskAgent" 8002 "agents.exchange_task_agent:app"

print_status "All services started!"

# ============================================
# 7. Display Status
# ============================================
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}System is ready!${NC}"
echo -e "${GREEN}================================${NC}"

echo ""
echo "Services:"
echo "  📡 FastAPI Server:        http://localhost:8000"
echo "  🤖 Assign Task Agent:     http://localhost:8001"
echo "  🤖 Exchange Task Agent:   http://localhost:8002"
echo ""
echo "Documentation:"
echo "  📚 API Docs:              http://localhost:8000/docs"
echo "  📚 ReDoc:                 http://localhost:8000/redoc"
echo ""
echo "Logs:"
echo "  📄 FastAPI:               logs/FastAPI.log"
echo "  📄 AssignTaskAgent:       logs/AssignTaskAgent.log"
echo "  📄 ExchangeTaskAgent:     logs/ExchangeTaskAgent.log"
echo ""
echo "Stop services:"
echo "  ./stop.sh"
echo ""


# ============================================
# stop.sh - Script để dừng hệ thống
# ============================================
# cat > stop.sh << 'STOPEOF'
#!/bin/bash
# Stop all services

echo "Stopping all services..."

# Function to stop service
stop_service() {
    local service_name=$1
    local pid_file=logs/${service_name}.pid
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill $pid
            echo "✓ Stopped $service_name (PID: $pid)"
            rm "$pid_file"
        fi
    fi
}

stop_service "FastAPI"
stop_service "AssignTaskAgent"
stop_service "ExchangeTaskAgent"

echo "All services stopped"
# STOPEOF
# chmod +x stop.sh


# ============================================
# docker-compose-full.yml
# ============================================
# Complete Docker Compose for all services

version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: auto_pm_db
    environment:
      POSTGRES_USER: ${DB_USER:-user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
      POSTGRES_DB: ${DB_NAME:-auto_project_manager}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - auto_pm_network

  # FastAPI Server
  fastapi:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: auto_pm_api
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${DB_USER:-user}:${DB_PASSWORD:-password}@postgres:5432/${DB_NAME:-auto_project_manager}
      SERVER_BASE_URL: http://fastapi:8000
      ASSIGN_TASK_AGENT_URL: http://assign_agent:8001/api/agents/assign-task
      EXCHANGE_TASK_AGENT_URL: http://exchange_agent:8002/api/agents/exchange-task
      ZALO_ACCESS_TOKEN: ${ZALO_ACCESS_TOKEN}
      ZALO_OA_ID: ${ZALO_OA_ID}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./qrcodes:/app/qrcodes
      - ./logs:/app/logs
    networks:
      - auto_pm_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Assign Task Agent
  assign_agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: auto_pm_assign_agent
    command: uvicorn agents.assign_task_agent:app --host 0.0.0.0 --port 8001
    ports:
      - "8001:8001"
    environment:
      LOG_LEVEL: INFO
    networks:
      - auto_pm_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Exchange Task Agent
  exchange_agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: auto_pm_exchange_agent
    command: uvicorn agents.exchange_task_agent:app --host 0.0.0.0 --port 8002
    ports:
      - "8002:8002"
    environment:
      LOG_LEVEL: INFO
    networks:
      - auto_pm_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:

networks:
  auto_pm_network:
    driver: bridge


# ============================================
# Dockerfile - For FastAPI
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p logs qrcodes

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# ============================================
# Dockerfile.agent - For Agents
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports (will be overridden)
EXPOSE 8001 8002

# Default command (will be overridden in docker-compose)
CMD ["uvicorn", "agents.assign_task_agent:app", "--host", "0.0.0.0", "--port", "8001"]


# ============================================
# deploy.sh - Deployment Script
# ============================================
#!/bin/bash

# Deploy to production server

set -e

echo "Auto Project Manager - Deployment Script"
echo "=========================================="

# Configuration
DEPLOY_USER=${DEPLOY_USER:-ubuntu}
DEPLOY_HOST=${DEPLOY_HOST:-your_server_ip}
DEPLOY_PATH=${DEPLOY_PATH:-/home/ubuntu/auto_project_manager}
GITHUB_REPO=${GITHUB_REPO:-https://github.com/your-repo.git}
BRANCH=${BRANCH:-main}

echo "Deployment Configuration:"
echo "  User: $DEPLOY_USER"
echo "  Host: $DEPLOY_HOST"
echo "  Path: $DEPLOY_PATH"
echo "  Repo: $GITHUB_REPO"
echo "  Branch: $BRANCH"

# 1. Connect and prepare server
echo ""
echo "Connecting to server..."

ssh $DEPLOY_USER@$DEPLOY_HOST << 'SSHEOF'
set -e

echo "Preparing server..."

# Check if directory exists
if [ ! -d "$DEPLOY_PATH" ]; then
    mkdir -p $DEPLOY_PATH
    git clone $GITHUB_REPO $DEPLOY_PATH
fi

cd $DEPLOY_PATH

# Pull latest changes
git fetch origin
git checkout origin/$BRANCH
git pull origin $BRANCH

# Stop current services
if [ -f "stop.sh" ]; then
    ./stop.sh
fi

sleep 2

# Start new services
chmod +x startup.sh
./startup.sh

echo "✓ Deployment completed"
SSHEOF

echo ""
echo "✓ Deployment successful!"
echo ""
echo "Next steps:"
echo "  1. Verify services are running:"
echo "     ssh $DEPLOY_USER@$DEPLOY_HOST 'docker ps' or check port 8000"
echo "  2. Check logs:"
echo "     ssh $DEPLOY_USER@$DEPLOY_HOST 'tail -f $DEPLOY_PATH/logs/FastAPI.log'"
echo "  3. Test API:"
echo "     curl http://$DEPLOY_HOST:8000/health"


# ============================================
# Development Quick Start
# ============================================

# Quick start for development:
# 1. Copy requirements.txt example and install
# 2. Copy .env.example to .env and edit
# 3. Run: python -c "from database import init_db; init_db()"
# 4. Run FastAPI: uvicorn main:app --reload
# 5. Run agents in separate terminals:
#    - uvicorn agents.assign_task_agent:app --reload --port 8001
#    - uvicorn agents.exchange_task_agent:app --reload --port 8002

# Production Notes:
# - Use PostgreSQL instead of SQLite
# - Set up SSL/HTTPS (Nginx reverse proxy)
# - Configure firewall rules
# - Use environment-specific .env files
# - Set up monitoring and alerting
# - Configure backups for database
# - Use process manager (systemd, supervisor)
# - Set up CI/CD pipeline