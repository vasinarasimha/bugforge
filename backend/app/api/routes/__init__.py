from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.issues import router as issues_router
from app.api.routes.projects import router as projects_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.sprints import router as sprints_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.teams import router as teams_router
from app.api.routes.super_admin import router as super_admin_router
from app.api.routes.company import router as company_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.ai import router as ai_router, qa_router

__all__ = [
    "auth_router",
    "admin_router",
    "dashboard_router",
    "issues_router",
    "projects_router",
    "uploads_router",
    "sprints_router",
    "analytics_router",
    "teams_router",
    "super_admin_router",
    "company_router",
    "notifications_router",
    "ai_router",
    "qa_router",
]


