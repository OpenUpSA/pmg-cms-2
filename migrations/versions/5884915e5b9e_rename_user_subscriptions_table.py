"""rename user_subscriptions table

Revision ID: 5884915e5b9e
Revises: 12a96feff6d7
Create Date: 2015-01-29 15:47:43.297368

"""

# revision identifiers, used by Alembic.
revision = '5884915e5b9e'
down_revision = '12a96feff6d7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('user_committee', 'user_committee_alerts')


def downgrade():
    op.rename_table('user_committee_alerts', 'user_committee')
