"""populate ministers

Revision ID: 49bcd2baee03
Revises: 1cda3dd1789
Create Date: 2015-09-03 12:19:19.523381

"""

# revision identifiers, used by Alembic.
revision = '49bcd2baee03'
down_revision = '1cda3dd1789'

from alembic import op
import sqlalchemy as sa


def upgrade():
    from pmg.models import Minister, Committee, db

    # populate with data
    items = """
    37:Minister of Agriculture, Forestry and Fisheries
    106:Minister of Arts and Culture
    28:Minister of Basic Education
    103:Minister of Communications
    65:Minister of Cooperative Governance and Traditional Affairs
    40:Minister of Correctional Services
    87:Minister of Defence and Military Veterans
    2:Minister of Economic Development
    3:Minister of Energy
    108:Minister of Environmental Affairs
    24:Minister of Finance Standing Committee
    63:Minister of Health
    64:Minister of Higher Education and Training
    110:Minister of Home Affairs
    91:Minister of Human Settlements
    49:Minister of International Relations
    38:Minister of Justice and Correctional Services
    62:Minister of Labour
    58:Minister of Mineral Resources
    86:Minister of Police
    73:Minister of Public Enterprises
    71:Minister of Public Service and Administration
    32:Minister of Public Works
    95:Minister of Rural Development and Land Reform
    23:Minister of Science and Technology
    116:Minister of Small Business Development
    19:Minister of Social Development
    94:Minister of Sport and Recreation
    117:Minister of Telecommunications and Postal Services
    9:Minister of Tourism
    98:Minister of Trade and Industry
    26:Minister of Transport
    111:Minister of Water and Sanitation
    51:Minister of Women in The Presidency
    :Minister in the Presidency
    84:Minister of State Security"""
    for item in items.strip().split("\n"):
        item = item.strip()
        cte_id, name = item.split(':', 1)

        m = Minister()
        m.name = name
        db.session.add(m)

        if cte_id:
            Committee.query.get(cte_id).minister = m

        db.session.commit()

    Committee.query.get(40).minister = Minister.query.filter(Minister.name == 'Minister of Justice and Correctional Services').one()
    Committee.query.get(55).minister = Minister.query.filter(Minister.name == 'Minister in the Presidency').one()
    Committee.query.get(30).minister = Minister.query.filter(Minister.name == 'Minister in the Presidency').one()
    db.session.commit()


def downgrade():
    op.execute("DELETE FROM minister")
