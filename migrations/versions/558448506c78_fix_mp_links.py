"""fix-mp-links

Revision ID: 558448506c78
Revises: 625399a9e26
Create Date: 2015-11-03 09:32:12.566944

"""

# revision identifiers, used by Alembic.
revision = '558448506c78'
down_revision = '625399a9e26'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
        UPDATE member
        SET pa_link = CONCAT('http://www.pa.org.za', pa_link)
        WHERE pa_link IS NOT NULL AND LEFT(pa_link, 5) != 'http:'
    """)
    pass


def downgrade():
    pass
