"""create projects and issues tables"""
import sqlalchemy as sa

from alembic import op

revision = "20260726_0002"
down_revision = "20260725_0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("projects", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_name", sa.String(160), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_table("issues", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("priority", sa.String(32), nullable=False), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_issues_project_id", "issues", ["project_id"])

def downgrade():
    op.drop_index("ix_issues_project_id", table_name="issues"); op.drop_table("issues"); op.drop_table("projects")
