"""add ondelete cascade to organisation_committee

Revision ID: 15cc05702df3
Revises: 29978548fcb6
Create Date: 2015-02-10 09:58:45.663899

"""

# revision identifiers, used by Alembic.
revision = '15cc05702df3'
down_revision = '29978548fcb6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("organisation_committee_committee_id_fkey", 'organisation_committee')
    op.create_foreign_key('organisation_committee_committee_id_fkey', 'organisation_committee', 'committee', ['committee_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint("organisation_committee_organisation_id_fkey", 'organisation_committee')
    op.create_foreign_key('organisation_committee_organisation_id_fkey', 'organisation_committee', 'organisation', ['organisation_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
