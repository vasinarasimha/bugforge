from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, joinedload

from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.models.role import Role


class TeamRepository:
    def list_teams(
        self,
        db: Session,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        pm_id: Optional[int] = None,
        tl_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[Team]:
        stmt = (
            select(Team)
            .options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members).joinedload(TeamMember.user).joinedload(User.roles),
            )
            .order_by(Team.id.asc())
        )

        if is_active is not None:
            stmt = stmt.where(Team.is_active == is_active)

        if pm_id is not None:
            stmt = stmt.where(Team.project_manager_id == pm_id)

        if tl_id is not None:
            stmt = stmt.where(Team.team_leader_id == tl_id)

        if user_id is not None:
            stmt = stmt.join(Team.members).where(TeamMember.user_id == user_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Team.name.ilike(term),
                    Team.description.ilike(term),
                )
            )

        return list(db.scalars(stmt).unique().all())

    def get_by_id(self, db: Session, team_id: int) -> Optional[Team]:
        stmt = (
            select(Team)
            .options(
                joinedload(Team.team_leader),
                joinedload(Team.project_manager),
                joinedload(Team.members).joinedload(TeamMember.user).joinedload(User.roles),
            )
            .where(Team.id == team_id)
        )
        return db.scalar(stmt)

    def get_by_name(self, db: Session, name: str) -> Optional[Team]:
        return db.scalar(select(Team).where(func.lower(Team.name) == name.lower().strip()))

    def get_team_by_leader_id(self, db: Session, leader_id: int) -> Optional[Team]:
        return db.scalar(select(Team).where(Team.team_leader_id == leader_id, Team.is_active == True))

    def create(
        self,
        db: Session,
        team: Team,
        member_ids: Optional[List[int]] = None
    ) -> Team:
        db.add(team)
        db.flush()

        if member_ids:
            # Filter real users only
            valid_users = db.scalars(
                select(User).where(User.id.in_(member_ids), User.is_system_user == False, User.is_active == True)
            ).all()
            for u in valid_users:
                db.add(TeamMember(team_id=team.id, user_id=u.id))

        db.commit()
        return self.get_by_id(db, team.id)

    def update(
        self,
        db: Session,
        team: Team,
        update_data: dict,
        member_ids: Optional[List[int]] = None
    ) -> Team:
        for k, v in update_data.items():
            if hasattr(team, k):
                setattr(team, k, v)

        if member_ids is not None:
            # Replace team members
            db.query(TeamMember).filter(TeamMember.team_id == team.id).delete()
            valid_users = db.scalars(
                select(User).where(User.id.in_(member_ids), User.is_system_user == False, User.is_active == True)
            ).all()
            for u in valid_users:
                db.add(TeamMember(team_id=team.id, user_id=u.id))

        db.commit()
        return self.get_by_id(db, team.id)

    def deactivate(self, db: Session, team: Team) -> Team:
        team.is_active = False
        db.commit()
        db.refresh(team)
        return team

    def get_available_team_leaders(self, db: Session, exclude_team_id: Optional[int] = None) -> List[User]:
        """
        Return users with Team Leader role who are not already assigned as Team Leader to another team.
        Excludes system users.
        """
        # Find team leader user IDs that are currently assigned to other active teams
        query = select(Team.team_leader_id).where(Team.team_leader_id.isnot(None), Team.is_active == True)
        if exclude_team_id:
            query = query.where(Team.id != exclude_team_id)
        assigned_tl_ids = set(db.scalars(query).all())

        # Find all active users with Team Leader role (excluding system users)
        tl_users = db.scalars(
            select(User)
            .join(User.roles)
            .where(
                Role.name == UserRole.TEAM_LEADER.value,
                User.is_system_user == False,
                User.is_active == True
            )
            .order_by(User.full_name.asc())
        ).unique().all()

        return [u for u in tl_users if u.id not in assigned_tl_ids]

    def get_all_eligible_employees(self, db: Session) -> List[User]:
        """
        Return all real active employees available for team membership.
        Excludes system users.
        """
        return list(
            db.scalars(
                select(User)
                .options(joinedload(User.roles))
                .where(
                    User.is_system_user == False,
                    User.is_active == True
                )
                .order_by(User.full_name.asc())
            ).unique().all()
        )
