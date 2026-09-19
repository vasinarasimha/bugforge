import logging
import os

logger = logging.getLogger(__name__)
logger.info("Starting FastAPI application...")

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import engine, SessionLocal
from app.models.user import UserRole
from app.services.notification_service import notification_service

from app.api.routes import (
    admin_router,
    auth_router,
    dashboard_router,
    issues_router,
    projects_router,
    sprints_router,
    uploads_router,
    analytics_router,
    teams_router,
    super_admin_router,
    company_router,
    notifications_router,
)
try:
    from app.api.routes.ai import router as ai_router
except ImportError:
    ai_router = None
try:
    from app.api.routes.copilot import router as copilot_router, alt_router as alt_copilot_router
except ImportError:
    copilot_router = None
    alt_copilot_router = None

settings = get_settings()


async def daily_read_notifications_cleanup_loop():
    """
    Background worker that runs daily to purge read notifications.
    Strictly preserves all unread notifications.
    """
    await asyncio.sleep(10)
    while True:
        try:
            db = SessionLocal()
            try:
                deleted = notification_service.cleanup_read_notifications(db, older_than_days=1)
                if deleted > 0:
                    logger.info(f"Automated daily cleanup: purged {deleted} read notification(s).")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error during automated daily notification cleanup: {e}", exc_info=True)
        # Sleep for 24 hours (86400 seconds)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(daily_read_notifications_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    openapi_url="/api/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(super_admin_router, prefix="/api", tags=["super-admin"])
app.include_router(company_router, prefix="/api", tags=["company"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(admin_router, prefix="/api", tags=["admin"])
app.include_router(teams_router, prefix="/api", tags=["teams"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(issues_router, prefix="/api", tags=["issues"])
app.include_router(projects_router, prefix="/api", tags=["projects"])
app.include_router(sprints_router, prefix="/api", tags=["sprints"])
app.include_router(uploads_router, prefix="/api", tags=["uploads"])
if ai_router:
    app.include_router(ai_router, prefix="/api", tags=["ai"])
if copilot_router:
    app.include_router(copilot_router, prefix="/api", tags=["copilot"])
if alt_copilot_router:
    app.include_router(alt_copilot_router, prefix="/api", tags=["copilot"])

uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


