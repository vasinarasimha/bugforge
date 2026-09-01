print('app/main.py Starting FastAPI application...')
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import engine
from app.models.user import UserRole

from app.api.routes import (
    admin_router,
    auth_router,
    dashboard_router,
    issues_router,
    projects_router,
    sprints_router,
    uploads_router,
    analytics_router,
    teams_router
)
try:
    from app.api.routes.ai import router as ai_router
except ImportError:
    ai_router = None

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    openapi_url="/api/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api", tags=["auth"])
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

uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


