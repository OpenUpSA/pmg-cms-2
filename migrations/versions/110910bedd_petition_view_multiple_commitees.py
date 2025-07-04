"""Petition View - multiple commitees

Revision ID: 110910bedd
Revises: 3118156286b
Create Date: 2025-06-26 08:10:50.296041

"""

# revision identifiers, used by Alembic.
revision = '110910bedd'
down_revision = '3118156286b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('petition_committee_join',
    sa.Column('petition_id', sa.Integer(), nullable=True),
    sa.Column('committee_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['committee_id'], ['committee.id'], name=op.f('fk_petition_committee_join_committee_id_committee'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['petition_id'], ['petition.id'], name=op.f('fk_petition_committee_join_petition_id_petition'), ondelete='CASCADE')
    )
    op.drop_constraint('fk_petition_committee_id_committee', 'petition', type_='foreignkey')
    op.drop_column('petition', 'committee_id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('petition', sa.Column('committee_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('fk_petition_committee_id_committee', 'petition', 'committee', ['committee_id'], ['id'])
    op.drop_table('petition_committee_join')
    ### end Alembic commands ###
