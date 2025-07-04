"""Remove petition_meeting_join table, use event_petitions instead

Revision ID: 1628ea2a5b6
Revises: fba65ba89b
Create Date: 2025-06-26 10:41:59.462054

"""

# revision identifiers, used by Alembic.
revision = '1628ea2a5b6'
down_revision = 'fba65ba89b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('petition_meeting_join')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('petition_meeting_join',
    sa.Column('petition_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('meeting_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['meeting_id'], ['event.id'], name='fk_petition_meeting_join_meeting_id_event', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['petition_id'], ['petition.id'], name='fk_petition_meeting_join_petition_id_petition', ondelete='CASCADE')
    )
    ### end Alembic commands ###
