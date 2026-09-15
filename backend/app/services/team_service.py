from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.team import TeamCreate, TeamUpdate, TeamRead, TeamMemberRead, TeamLeaderRead, ProjectManagerRead, AvailableEmployee


class TeamService:
    def __init__(self):
        self.team_repository = TeamRepository()
        self.user_repository = UserRepository()

    def serialize_team(self, team: Team) -> Dict[str, Any]:
        members_data = []
        for m in getattr(team, 'members', []):
            if m.user:
                role_name = m.user.roles[0].name if m.user.roles else "Developer"
                members_data.append(
                    TeamMemberRead(
                        id=m.id,
                        user_id=m.user.id,
                        full_name=m.user.full_name,
                        email=m.user.email,
                        job_title=m.user.job_title,
                        department=m.user.department,
                        role=role_name,
                        joined_at=m.joined_at,
                    )
                )

        tl_data = None
        if team.team_leader:
            tl_data = TeamLeaderRead(
                id=team.team_leader.id,
                full_name=team.team_leader.full_name,
                email=team.team_leader.email,
                job_title=team.team_leader.job_title,
            )

        pm_data = None
        if team.project_manager:
            pm_data = ProjectManagerRead(
                id=team.project_manager.id,
                full_name=team.project_manager.full_name,
                email=team.project_manager.email,
                job_title=team.project_manager.job_title,
            )

        return {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "team_leader_id": team.team_leader_id,
            "team_leader": tl_data,
            "project_manager_id": team.project_manager_id,
            "project_manager": pm_data,
            "is_active": team.is_active,
            "member_count": len(members_data),
            "members": members_data,
            "created_at": team.created_at,
            "updated_at": team.updated_at,
        }

    def list_teams(
        self,
        db: Session,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        pm_id: Optional[int] = None,
        tl_id: Optional[int] = None,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        teams = self.team_repository.list_teams(
            db=db,
            search=search,
            is_active=is_active,
            pm_id=pm_id,
            tl_id=tl_id,
            user_id=user_id,
            company_id=company_id,
        )
        return [self.serialize_team(t) for t in teams]

    def get_team(self, db: Session, team_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        team = self.team_repository.get_by_id(db, team_id, company_id=company_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found."
            )
        return self.serialize_team(team)

    def create_team(self, db: Session, data: TeamCreate, current_user: Optional[User] = None) -> Dict[str, Any]:
        company_id = None
        if current_user:
            user_roles = [r.name for r in getattr(current_user, 'roles', [])]
            if "Super Admin" in user_roles:
                company_id = getattr(data, "company_id", None) or current_user.company_id or 1
            else:
                company_id = current_user.company_id or 1
        else:
            company_id = getattr(data, "company_id", None) or 1

        # Validate team name uniqueness within company
        existing = self.team_repository.get_by_name(db, data.name, company_id=company_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A team with name '{data.name}' already exists."
            )

        # Validate Team Leader
        if data.team_leader_id:
            tl_user = self.user_repository.get_by_id(db, data.team_leader_id, company_id=company_id)
            if not tl_user and company_id == 1:
                tl_candidate = self.user_repository.get_by_id(db, data.team_leader_id)
                if tl_candidate and (tl_candidate.company_id is None or tl_candidate.company_id == 1):
                    tl_user = tl_candidate
            if not tl_user or tl_user.is_system_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected Team Leader user does not exist or does not belong to your company."
                )
            # Check if this TL is already leading another active team within company
            existing_team = self.team_repository.get_team_by_leader_id(db, data.team_leader_id, company_id=company_id)
            if existing_team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee '{tl_user.full_name}' is already the Team Leader of '{existing_team.name}'. A Team Leader can belong to only ONE team."
                )

        # Validate Project Manager (if provided)
        if data.project_manager_id:
            pm_user = self.user_repository.get_by_id(db, data.project_manager_id, company_id=company_id)
            if not pm_user and company_id == 1:
                pm_candidate = self.user_repository.get_by_id(db, data.project_manager_id)
                if pm_candidate and (pm_candidate.company_id is None or pm_candidate.company_id == 1):
                    pm_user = pm_candidate
            if not pm_user or pm_user.is_system_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected Project Manager user does not exist or does not belong to your company."
                )

        team = Team(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            team_leader_id=data.team_leader_id,
            project_manager_id=data.project_manager_id,
            is_active=data.is_active,
            company_id=company_id,
        )

        created_team = self.team_repository.create(db, team, data.member_ids)
        return self.serialize_team(created_team)

    def update_team(self, db: Session, team_id: int, data: TeamUpdate, current_user: Optional[User] = None) -> Dict[str, Any]:
        company_id = None
        if current_user:
            user_roles = [r.name for r in getattr(current_user, 'roles', [])]
            if "Super Admin" not in user_roles:
                company_id = current_user.company_id

        team = self.team_repository.get_by_id(db, team_id, company_id=company_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found."
            )

        update_fields = {}

        if data.name is not None and data.name.strip():
            # Check uniqueness if name changed within team's company
            if data.name.strip().lower() != team.name.lower():
                existing = self.team_repository.get_by_name(db, data.name.strip(), company_id=team.company_id)
                if existing and existing.id != team_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"A team with name '{data.name}' already exists."
                    )
            update_fields["name"] = data.name.strip()

        if data.description is not None:
            update_fields["description"] = data.description.strip() if data.description else None

        if data.team_leader_id is not None:
            if data.team_leader_id != team.team_leader_id:
                tl_user = self.user_repository.get_by_id(db, data.team_leader_id, company_id=team.company_id)
                if not tl_user and team.company_id == 1:
                    tl_candidate = self.user_repository.get_by_id(db, data.team_leader_id)
                    if tl_candidate and (tl_candidate.company_id is None or tl_candidate.company_id == 1):
                        tl_user = tl_candidate
                if not tl_user or tl_user.is_system_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected Team Leader user does not exist or does not belong to this company."
                    )
                # Check uniqueness across other teams in the same company
                existing_team = self.team_repository.get_team_by_leader_id(db, data.team_leader_id, company_id=team.company_id)
                if existing_team and existing_team.id != team_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Employee '{tl_user.full_name}' is already the Team Leader of '{existing_team.name}'. A Team Leader can belong to only ONE team."
                    )
            update_fields["team_leader_id"] = data.team_leader_id

        if data.project_manager_id is not None:
            if data.project_manager_id != team.project_manager_id:
                pm_user = self.user_repository.get_by_id(db, data.project_manager_id, company_id=team.company_id)
                if not pm_user and team.company_id == 1:
                    pm_candidate = self.user_repository.get_by_id(db, data.project_manager_id)
                    if pm_candidate and (pm_candidate.company_id is None or pm_candidate.company_id == 1):
                        pm_user = pm_candidate
                if not pm_user or pm_user.is_system_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected Project Manager user does not exist or does not belong to this company."
                    )
            update_fields["project_manager_id"] = data.project_manager_id

        if data.is_active is not None:
            update_fields["is_active"] = data.is_active

        updated_team = self.team_repository.update(db, team, update_fields, data.member_ids)
        return self.serialize_team(updated_team)

    def deactivate_team(self, db: Session, team_id: int, current_user: Optional[User] = None) -> Dict[str, Any]:
        company_id = None
        if current_user:
            user_roles = [r.name for r in getattr(current_user, 'roles', [])]
            if "Super Admin" not in user_roles:
                company_id = current_user.company_id

        team = self.team_repository.get_by_id(db, team_id, company_id=company_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {team_id} not found."
            )
        deactivated = self.team_repository.deactivate(db, team)
        return {
            "message": f"Team '{deactivated.name}' deactivated successfully.",
            "team": self.serialize_team(deactivated),
        }

    def get_meta_available_leaders(self, db: Session, exclude_team_id: Optional[int] = None, company_id: Optional[int] = None) -> List[Dict[str, Any]]:
        leaders = self.team_repository.get_available_team_leaders(db, exclude_team_id, company_id=company_id)
        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "job_title": u.job_title,
                "department": u.department,
            }
            for u in leaders
        ]

    def get_meta_available_members(self, db: Session, company_id: Optional[int] = None) -> List[Dict[str, Any]]:
        employees = self.team_repository.get_all_eligible_employees(db, company_id=company_id)
        # Find which team each employee currently belongs to within company
        all_teams = self.team_repository.list_teams(db, company_id=company_id)
        user_team_map = {}
        user_lead_map = {}
        for t in all_teams:
            if t.team_leader_id:
                user_lead_map[t.team_leader_id] = (t.id, t.name)
            for m in t.members:
                if m.user_id:
                    user_team_map[m.user_id] = (t.id, t.name)

        result = []
        for u in employees:
            role_name = u.roles[0].name if u.roles else "Developer"
            team_info = user_team_map.get(u.id)
            lead_info = user_lead_map.get(u.id)

            result.append(
                AvailableEmployee(
                    id=u.id,
                    full_name=u.full_name,
                    email=u.email,
                    job_title=u.job_title,
                    department=u.department,
                    role=role_name,
                    current_team_id=team_info[0] if team_info else None,
                    current_team_name=team_info[1] if team_info else None,
                    is_assigned_as_leader=bool(lead_info),
                ).model_dump()
            )
        return result

    def get_team_stats(self, db: Session, company_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculates high-level team management statistics & workforce telemetry:
        - Total and active team counts
        - Total eligible application users/employees (excluding FastAPI system users)
        - Count of members assigned to active teams
        - Count of unassigned employees
        - Total designated team leaders
        """
        team_q = db.query(func.count(Team.id))
        active_team_q = db.query(func.count(Team.id)).filter(Team.is_active == True)
        user_q = db.query(func.count(User.id)).filter(User.is_system_user == False, User.is_active == True)
        assigned_q = (
            db.query(func.count(distinct(TeamMember.user_id)))
            .join(Team, Team.id == TeamMember.team_id)
            .join(User, User.id == TeamMember.user_id)
            .filter(Team.is_active == True, User.is_system_user == False, User.is_active == True)
        )
        leader_q = (
            db.query(func.count(distinct(Team.team_leader_id)))
            .filter(Team.is_active == True, Team.team_leader_id.isnot(None))
        )

        if company_id is not None:
            team_q = team_q.filter(Team.company_id == company_id)
            active_team_q = active_team_q.filter(Team.company_id == company_id)
            user_q = user_q.filter(User.company_id == company_id)
            assigned_q = assigned_q.filter(Team.company_id == company_id)
            leader_q = leader_q.filter(Team.company_id == company_id)

        total_teams = team_q.scalar() or 0
        active_teams = active_team_q.scalar() or 0
        inactive_teams = max(0, total_teams - active_teams)
        total_users = user_q.scalar() or 0
        assigned_members = assigned_q.scalar() or 0
        unassigned_users = max(0, total_users - assigned_members)
        total_leaders = leader_q.scalar() or 0

        return {
            "total_teams": total_teams,
            "active_teams": active_teams,
            "inactive_teams": inactive_teams,
            "total_users": total_users,
            "assigned_members": assigned_members,
            "unassigned_users": unassigned_users,
            "total_leaders": total_leaders,
        }
