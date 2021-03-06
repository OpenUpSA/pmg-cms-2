"""Add nid field to Redirect model.

Revision ID: 4bd2c7b6ed8a
Revises: 414f1f4508c
Create Date: 2015-01-30 09:16:58.025681

"""

# revision identifiers, used by Alembic.
revision = '4bd2c7b6ed8a'
down_revision = '414f1f4508c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('redirect', sa.Column('nid', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('redirect', 'nid')
    ### end Alembic commands ###
