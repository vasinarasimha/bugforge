"""create pgvector extension

Revision ID: 77a905bee94a
Revises: 812616929bc0
Create Date: 2026-08-20 18:49:13.324239
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '77a905bee94a'
down_revision: Union[str, Sequence[str], None] = '812616929bc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
