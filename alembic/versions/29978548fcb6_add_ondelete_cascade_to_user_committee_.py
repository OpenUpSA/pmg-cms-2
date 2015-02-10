"""add ondelete cascade to user_committee_alerts

Revision ID: 29978548fcb6
Revises: 1cde07889540
Create Date: 2015-02-10 09:53:41.732800

"""

# revision identifiers, used by Alembic.
revision = '29978548fcb6'
down_revision = '1cde07889540'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("user_committee_user_id_fkey", 'user_committee_alerts')
    op.create_foreign_key('user_committee_alerts_user_id_fkey', 'user_committee_alerts', 'user', ['user_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint("user_committee_committee_id_fkey", 'user_committee_alerts')
    op.create_foreign_key('user_committee_alerts_committee_id_fkey', 'user_committee_alerts', 'committee', ['committee_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint("user_committee_alerts_user_id_fkey", 'user_committee_alerts')
    op.create_foreign_key('user_committee_user_id_fkey', 'user_committee_alerts', 'user', ['user_id'], ['id'])

    op.drop_constraint("user_committee_alerts_committee_id_fkey", 'user_committee_alerts')
    op.create_foreign_key('user_committee_committee_id_fkey', 'user_committee_alerts', 'committee', ['committee_id'], ['id'])
