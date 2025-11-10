"""Merge heads a1b2c3d4e5f6 and 1729ea3b7c8f

Revision ID: 1337c883f34
Revises: ('a1b2c3d4e5f6', '1729ea3b7c8f')
Create Date: 2025-11-10 12:53:42.459915

"""

# revision identifiers, used by Alembic.
revision = '1337c883f34'
down_revision = ('a1b2c3d4e5f6', '1729ea3b7c8f')

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
