"""add pgvector extension and ensure embedding column

Revision ID: a541755a590a
Revises: 001a7c65c912
Create Date: 2026-08-20 18:47:29.760205
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a541755a590a'
down_revision: Union[str, Sequence[str], None] = '001a7c65c912'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
