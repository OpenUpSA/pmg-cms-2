"""Add additional ministers to committees

Revision ID: 3c1a7e5d9b2f
Revises: 248d10b76bb
Create Date: 2026-10-29 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = '3c1a7e5d9b2f'
down_revision = '248d10b76bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'committee_additional_minister',
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('minister_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['committee_id'], ['committee.id'], name=op.f('fk_committee_additional_minister_committee_id_committee'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['minister_id'], ['minister.id'], name=op.f('fk_committee_additional_minister_minister_id_minister'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('committee_id', 'minister_id', name=op.f('pk_committee_additional_minister')),
    )


def downgrade():
    op.drop_table('committee_additional_minister')
