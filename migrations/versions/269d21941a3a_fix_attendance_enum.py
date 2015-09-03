"""fix_attendance_enum

Revision ID: 269d21941a3a
Revises: 44d9d3bf2abb
Create Date: 2015-07-21 17:47:08.251880

"""

# revision identifiers, used by Alembic.
revision = '269d21941a3a'
down_revision = '44d9d3bf2abb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("COMMIT")
    op.execute("ALTER TYPE meeting_attendance_enum ADD VALUE 'U' AFTER 'Y'")


def downgrade():
    pass
