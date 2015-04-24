"""bill_must_have_type

Revision ID: 3a69784c209f
Revises: 4e34e26ddbad
Create Date: 2015-04-24 14:04:43.125387

"""

# revision identifiers, used by Alembic.
revision = '3a69784c209f'
down_revision = '4e34e26ddbad'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('bill', 'type_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('bill', 'type_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    ### end Alembic commands ###
