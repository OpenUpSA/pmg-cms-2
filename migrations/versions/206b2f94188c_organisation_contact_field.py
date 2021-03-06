"""Organisation contact field

Revision ID: 206b2f94188c
Revises: 33ad6ad8f955
Create Date: 2015-02-04 17:06:42.951185

"""

# revision identifiers, used by Alembic.
revision = '206b2f94188c'
down_revision = '33ad6ad8f955'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organisation', sa.Column('contact', sa.String(length=255), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('organisation', 'contact')
    ### end Alembic commands ###
