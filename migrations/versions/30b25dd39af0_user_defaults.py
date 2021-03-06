"""User defaults

Revision ID: 30b25dd39af0
Revises: 46b85e11f48f
Create Date: 2015-02-12 15:34:59.515740

"""

# revision identifiers, used by Alembic.
revision = '30b25dd39af0'
down_revision = '46b85e11f48f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    ### end Alembic commands ###
