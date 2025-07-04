"""Added Petitions Table

Revision ID: 46fa8a10011
Revises: 35d477d67b7
Create Date: 2025-06-04 13:59:02.082946

"""

# revision identifiers, used by Alembic.
revision = '46fa8a10011'
down_revision = '35d477d67b7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('petition',
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('house_id', sa.Integer(), nullable=True),
    sa.Column('committee_id', sa.Integer(), nullable=True),
    sa.Column('issue', sa.String(length=255), nullable=True),
    sa.Column('petitioner', sa.String(length=255), nullable=True),
    sa.Column('report_id', sa.Integer(), nullable=True),
    sa.Column('hansard_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['committee_id'], ['committee.id'], name=op.f('fk_petition_committee_id_committee')),
    sa.ForeignKeyConstraint(['hansard_id'], ['event.id'], name=op.f('fk_petition_hansard_id_event')),
    sa.ForeignKeyConstraint(['house_id'], ['house.id'], name=op.f('fk_petition_house_id_house')),
    sa.ForeignKeyConstraint(['report_id'], ['file.id'], name=op.f('fk_petition_report_id_file')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_petition'))
    )
    op.create_index(op.f('ix_petition_created_at'), 'petition', ['created_at'], unique=False)
    op.create_index(op.f('ix_petition_updated_at'), 'petition', ['updated_at'], unique=False)
    op.create_table('petition_meeting_join',
    sa.Column('petition_id', sa.Integer(), nullable=True),
    sa.Column('meeting_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['meeting_id'], ['event.id'], name=op.f('fk_petition_meeting_join_meeting_id_event'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['petition_id'], ['petition.id'], name=op.f('fk_petition_meeting_join_petition_id_petition'), ondelete='CASCADE')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('petition_meeting_join')
    op.drop_index(op.f('ix_petition_updated_at'), table_name='petition')
    op.drop_index(op.f('ix_petition_created_at'), table_name='petition')
    op.drop_table('petition')
    ### end Alembic commands ###
