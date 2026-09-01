"""add teams table and system user flag

Revision ID: d4e5f6a7b8c9
Revises: f2b8c9d1e3a4
Create Date: 2026-08-31 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'f2b8c9d1e3a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_system_user column to users table
    op.add_column('users', sa.Column('is_system_user', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # 2. Flag the default FastAPI / development test accounts
    op.execute("UPDATE users SET is_system_user = true WHERE email IN ('admin@test.com', 'newuser@example.com')")

    # 3. Create teams table (if not already existing)
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('team_leader_id', sa.Integer(), nullable=True),
        sa.Column('project_manager_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_leader_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_manager_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_leader_id', name='uq_teams_team_leader_id')
    )
    op.create_index(op.f('ix_teams_team_leader_id'), 'teams', ['team_leader_id'], unique=False)
    op.create_index(op.f('ix_teams_project_manager_id'), 'teams', ['project_manager_id'], unique=False)

    # 4. Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member_team_user')
    )
    op.create_index(op.f('ix_team_members_team_id'), 'team_members', ['team_id'], unique=False)
    op.create_index(op.f('ix_team_members_user_id'), 'team_members', ['user_id'], unique=False)

    # 5. Initial setup: Put all real users into a single default team ("BugForge Core Team")
    op.execute("""
        DO $$
        DECLARE
            tl_id INT;
            pm_id INT;
            new_team_id INT;
        BEGIN
            -- Find TL and PM users if they exist
            SELECT id INTO tl_id FROM users WHERE email = 'vln@tl.in' LIMIT 1;
            SELECT id INTO pm_id FROM users WHERE email = 'vln@pm.in' LIMIT 1;

            -- Create the initial default team
            INSERT INTO teams (name, description, team_leader_id, project_manager_id, is_active, created_at, updated_at)
            VALUES ('BugForge Core Team', 'Primary engineering and cross-functional defect resolution team', tl_id, pm_id, true, NOW(), NOW())
            RETURNING id INTO new_team_id;

            -- Add all real active employees into this initial team
            INSERT INTO team_members (team_id, user_id, joined_at)
            SELECT new_team_id, id, NOW()
            FROM users
            WHERE is_system_user = false AND is_active = true
            ON CONFLICT (team_id, user_id) DO NOTHING;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_team_members_user_id'), table_name='team_members')
    op.drop_index(op.f('ix_team_members_team_id'), table_name='team_members')
    op.drop_table('team_members')

    op.drop_index(op.f('ix_teams_project_manager_id'), table_name='teams')
    op.drop_index(op.f('ix_teams_team_leader_id'), table_name='teams')
    op.drop_table('teams')

    op.drop_column('users', 'is_system_user')
