"""add ondelete set null to question_repyl, tabled_committee_report and call_for_comment tables

Revision ID: 122a38429a58
Revises: 29cf770ce19b
Create Date: 2015-02-10 10:13:58.437446

"""

# revision identifiers, used by Alembic.
revision = '122a38429a58'
down_revision = '29cf770ce19b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint("question_reply_committee_id_fkey", 'question_reply')
    op.create_foreign_key('question_reply_committee_id_fkey', 'question_reply', 'committee', ['committee_id'], ['id'], ondelete='SET NULL')

    op.drop_constraint("tabled_committee_report_committee_id_fkey", 'tabled_committee_report')
    op.create_foreign_key('tabled_committee_report_committee_id_fkey', 'tabled_committee_report', 'committee', ['committee_id'], ['id'], ondelete='SET NULL')

    op.drop_constraint("call_for_comment_committee_id_fkey", 'call_for_comment')
    op.create_foreign_key('call_for_comment_committee_id_fkey', 'call_for_comment', 'committee', ['committee_id'], ['id'], ondelete='SET NULL')


def downgrade():
    pass
