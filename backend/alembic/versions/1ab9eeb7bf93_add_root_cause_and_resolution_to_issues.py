"""Add root_cause and resolution to issues

Revision ID: 1ab9eeb7bf93
Revises: 6c1e95e02210
Create Date: 2026-08-27 14:02:58.113174
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1ab9eeb7bf93'
down_revision: Union[str, Sequence[str], None] = '6c1e95e02210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('issues', sa.Column('root_cause', sa.Text(), nullable=True))
    op.add_column('issues', sa.Column('resolution', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column('issues', 'resolution')
    op.drop_column('issues', 'root_cause')
    # ### end Alembic commands ###
