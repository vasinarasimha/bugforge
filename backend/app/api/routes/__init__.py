from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.issues import router as issues_router
from app.api.routes.projects import router as projects_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.sprints import router as sprints_router

__all__ = ["auth_router", "admin_router", "dashboard_router", "issues_router", "projects_router", "uploads_router", "sprints_router"]
