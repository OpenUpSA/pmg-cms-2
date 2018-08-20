"""populate-provincial-legislatures

Revision ID: 299e1d15a55f
Revises: 1f97f799a477
Create Date: 2018-08-20 16:17:28.919476

"""

# revision identifiers, used by Alembic.
revision = '299e1d15a55f'
down_revision = '1f97f799a477'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    Ensure all provinces exist as Provincial Legislatures
    """
    from pmg.models import House, db
    from pmg.utils import get_provincial_legislatures

    pls = [
        {
            'name': 'Eastern Cape Legislature',
            'name_short': 'EC'
        },
        {
            'name': 'Free State Legislature',
            'name_short': 'FS'
        },
        {
            'name': 'Gauteng Legislature',
            'name_short': 'GT'
        },
        {
            'name': 'KwaZulu-Natal Legislature',
            'name_short': 'KZN'
        },
        {
            'name': 'Limpopo Legislature',
            'name_short': 'LIM'
        },
        {
            'name': 'Mpumalanga Legislature',
            'name_short': 'MP'
        },
        {
            'name': 'Northern Cape Legislature',
            'name_short': 'NC'
        },
        {
            'name': 'North West Legislature',
            'name_short': 'NW'
        },
        {
            'name': 'Western Cape Parliament',
            'name_short': 'WC'
        }
    ]
    existing_pls = House.query.filter(House.sphere=='provincial').all()
    pl_codes = [p.name_short for p in existing_pls]

    for pl in pls:
        if pl['name_short'] not in pl_codes:

            new_pl = House()
            new_pl.name = pl['name']
            new_pl.name_short = pl['name_short']
            new_pl.sphere = 'provincial'

            db.session.add(new_pl)
    
    db.session.commit()


def downgrade():
    pass
