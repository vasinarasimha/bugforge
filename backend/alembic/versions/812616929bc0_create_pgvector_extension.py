"""create pgvector extension

Revision ID: 812616929bc0
Revises: a541755a590a
Create Date: 2026-08-20 18:48:41.503620
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '812616929bc0'
down_revision: Union[str, Sequence[str], None] = 'a541755a590a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
