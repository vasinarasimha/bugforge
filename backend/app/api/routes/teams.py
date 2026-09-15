from typing import Annotated, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role, get_effective_company_id, is_super_admin
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.team import TeamCreate, TeamUpdate, TeamRead, AvailableEmployee
from app.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["Teams"])
team_service = TeamService()


@router.get("", response_model=List[TeamRead], summary="List teams (Role-scoped)")
def list_teams(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """
    List teams based on role and authorized scope:
    - Super Admin: All teams across platform
    - Admin: All teams in their organization
    - Project Manager: Teams managed by PM within organization
    - Team Leader: Team led by TL within organization
    - Others: Teams where user is a member within organization
    """
    user_roles = [r.name for r in getattr(current_user, 'roles', [])]
    cid = get_effective_company_id(current_user)

    if "Super Admin" in user_roles:
        return team_service.list_teams(db, search=search, is_active=is_active)
    elif "Admin" in user_roles:
        return team_service.list_teams(db, search=search, is_active=is_active, company_id=cid)
    elif "Project Manager" in user_roles:
        return team_service.list_teams(db, search=search, is_active=is_active, pm_id=current_user.id, company_id=cid)
    elif "Team Leader" in user_roles:
        return team_service.list_teams(db, search=search, is_active=is_active, tl_id=current_user.id, company_id=cid)
    else:
        return team_service.list_teams(db, search=search, is_active=is_active, user_id=current_user.id, company_id=cid)


@router.get("/meta/available-leaders", summary="Get available Team Leaders (Admin only)")
def get_available_leaders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
    exclude_team_id: Optional[int] = None,
):
    """Get active Team Leader employees who are not already leading another team."""
    cid = get_effective_company_id(current_user)
    return team_service.get_meta_available_leaders(db, exclude_team_id=exclude_team_id, company_id=cid)


@router.get("/meta/available-members", response_model=List[AvailableEmployee], summary="Get available employees for team assignment (Admin only)")
def get_available_members(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Get all real employees eligible for team membership, excluding system test accounts."""
    cid = get_effective_company_id(current_user)
    return team_service.get_meta_available_members(db, company_id=cid)


@router.get("/meta/stats", summary="Get team management overview insights (Admin only)")
@router.get("/stats", summary="Get team management overview insights (Admin only)")
def get_team_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Get overall team and real user counts for Team Management insight cards."""
    cid = get_effective_company_id(current_user)
    return team_service.get_team_stats(db, company_id=cid)


@router.get("/{team_id}", response_model=TeamRead, summary="Get team by ID")
def get_team(
    team_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve team details by ID with permission check."""
    cid = get_effective_company_id(current_user)
    team_data = team_service.get_team(db, team_id, company_id=cid)
    user_roles = [r.name for r in getattr(current_user, 'roles', [])]

    # Non-admins can only view their own team / managed team
    if "Super Admin" not in user_roles and "Admin" not in user_roles:
        is_pm = team_data.get("project_manager_id") == current_user.id
        is_tl = team_data.get("team_leader_id") == current_user.id
        is_member = any(m.user_id == current_user.id for m in team_data.get("members", []))
        if not (is_pm or is_tl or is_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this team's details."
            )

    return team_data


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED, summary="Create a new team (Admin only)")
def create_team(
    data: TeamCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Create a new team with unique TL validation, optional PM, and initial members."""
    return team_service.create_team(db, data, current_user=current_user)


@router.put("/{team_id}", response_model=TeamRead, summary="Update team details and members (Admin only)")
def update_team(
    team_id: int,
    data: TeamUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Update team metadata, reassign TL/PM, or update member roster."""
    return team_service.update_team(db, team_id, data, current_user=current_user)


@router.delete("/{team_id}", summary="Deactivate a team (Admin only)")
def deactivate_team(
    team_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN]))],
):
    """Safely deactivate a team."""
    return team_service.deactivate_team(db, team_id, current_user=current_user)
