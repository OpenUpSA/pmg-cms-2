"""add ondelete set null to committee-member link

Revision ID: 29cf770ce19b
Revises: 28475567a3cf
Create Date: 2015-02-10 10:11:03.487014

"""

# revision identifiers, used by Alembic.
revision = '29cf770ce19b'
down_revision = '28475567a3cf'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("committee_members_committee_id_fkey", 'committee_members')
    op.create_foreign_key('committee_members_committee_id_fkey', 'committee_members', 'committee', ['committee_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
