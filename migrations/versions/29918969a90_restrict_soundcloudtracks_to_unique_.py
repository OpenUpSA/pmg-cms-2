"""Restrict SoundcloudTracks to unique file IDs

Revision ID: 29918969a90
Revises: 3c2b8a62b3f5
Create Date: 2016-09-01 17:20:50.154747

"""

# revision identifiers, used by Alembic.
revision = '29918969a90'
down_revision = '3c2b8a62b3f5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(op.f('soundcloud_track_file_id_key'), 'soundcloud_track', ['file_id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('soundcloud_track_file_id_key'), 'soundcloud_track', type_='unique')
    ### end Alembic commands ###
