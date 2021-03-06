"""add active boolean to committees

Revision ID: 39f25296cd6
Revises: 46085f5c8e36
Create Date: 2017-05-22 12:12:39.327466

"""

# revision identifiers, used by Alembic.
revision = '39f25296cd6'
down_revision = '46085f5c8e36'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('committee', sa.Column('active', sa.Boolean(), server_default=sa.text(u'true'), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('committee', 'active')
    ### end Alembic commands ###
