"""add_employee_contact_and_address_fields

Revision ID: f2b8c9d1e3a4
Revises: ea9f8fe8bc23
Create Date: 2026-08-31 10:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2b8c9d1e3a4'
down_revision: Union[str, Sequence[str], None] = 'ea9f8fe8bc23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mobile_country_code', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('mobile_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('address_line_1', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('address_line_2', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('state_code', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('country', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('country_code', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'country_code')
    op.drop_column('users', 'country')
    op.drop_column('users', 'state_code')
    op.drop_column('users', 'state')
    op.drop_column('users', 'city')
    op.drop_column('users', 'address_line_2')
    op.drop_column('users', 'address_line_1')
    op.drop_column('users', 'mobile_number')
    op.drop_column('users', 'mobile_country_code')
