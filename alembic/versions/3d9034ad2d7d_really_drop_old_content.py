"""really drop old content

Revision ID: 3d9034ad2d7d
Revises: 1dd2771cbf39
Create Date: 2015-03-29 12:01:54.276288

"""

# revision identifiers, used by Alembic.
revision = '3d9034ad2d7d'
down_revision = '1dd2771cbf39'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_table(u'old_content')


def downgrade():
    pass
