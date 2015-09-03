"""add ondelete set null to event-committee link

Revision ID: 28475567a3cf
Revises: 15cc05702df3
Create Date: 2015-02-10 10:08:40.376613

"""

# revision identifiers, used by Alembic.
revision = '28475567a3cf'
down_revision = '15cc05702df3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("event_committee_id_fkey", 'event')
    op.create_foreign_key('event_committee_id_fkey', 'event', 'committee', ['committee_id'], ['id'], ondelete='SET NULL')

def downgrade():
    pass
