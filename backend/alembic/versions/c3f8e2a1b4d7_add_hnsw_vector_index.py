"""add hnsw vector index on issues embedding_vector

Revision ID: c3f8e2a1b4d7
Revises: a541755a590a
Create Date: 2026-08-27 10:55:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c3f8e2a1b4d7'
down_revision: Union[str, Sequence[str], None] = 'a541755a590a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create HNSW index for efficient cosine distance searches on embedding_vector
    # HNSW provides fast approximate nearest neighbor search
    # m=16 and ef_construction=64 are good defaults for moderate dataset sizes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_issues_embedding_vector_hnsw
        ON issues
        USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_issues_embedding_vector_hnsw;")
