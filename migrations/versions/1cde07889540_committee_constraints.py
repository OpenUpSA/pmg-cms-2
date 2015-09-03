"""add ondelete cascade to user_committee foreign keys

Revision ID: 1cde07889540
Revises: 21fb154d61b5
Create Date: 2015-02-10 09:28:36.237326

"""

# revision identifiers, used by Alembic.
revision = '1cde07889540'
down_revision = '21fb154d61b5'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("user_committee_user_id_fkey1", 'user_committee')
    op.create_foreign_key('user_committee_user_id_fkey1', 'user_committee', 'user', ['user_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint("user_committee_committee_id_fkey1", 'user_committee')
    op.create_foreign_key('user_committee_committee_id_fkey1', 'user_committee', 'committee', ['committee_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
