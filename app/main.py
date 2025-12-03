from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.scheduler import start_scheduler, shutdown_scheduler


# Import routers
from app.routers import (
    webhooks, chatbot  
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler
    # logger.info("Starting task scheduler...")
    # start_scheduler()
    
    logger.info("Application started")
    yield
    
    # Shutdown
    logger.info("Shutting down scheduler...")
    shutdown_scheduler()
    logger.info("Application shutdown")


app = FastAPI(
    title="Auto Project Manager API",
    description="Automated project management with AI agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks.router)
app.include_router(chatbot.router)

# ============================================
# Health Check Endpoint
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/test/trigger-daily-notifications")
async def trigger_daily_notifications():
    """Test endpoint to manually trigger daily notifications"""
    from app.scheduler import send_daily_task_notifications
    await send_daily_task_notifications()
    return {"status": "Notifications triggered"}

# Backward compatibility: redirect old webhook endpoint to new one
@app.post("/webhook-zalooa")
async def zalo_webhook_redirect(request: dict, background_tasks: BackgroundTasks):
    """Redirect to new webhook endpoint for backward compatibility"""
    from app.routers.webhooks import zalo_webhook
    return await zalo_webhook(request, background_tasks)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5544)