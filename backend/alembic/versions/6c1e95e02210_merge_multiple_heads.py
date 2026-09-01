"""Merge multiple heads

Revision ID: 6c1e95e02210
Revises: 77a905bee94a, c3f8e2a1b4d7
Create Date: 2026-08-27 11:19:41.519081
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '6c1e95e02210'
down_revision: Union[str, Sequence[str], None] = ('77a905bee94a', 'c3f8e2a1b4d7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
