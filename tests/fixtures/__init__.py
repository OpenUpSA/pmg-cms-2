import pytz
import datetime
from fixture import DataSet, NamedDataStyle, SQLAlchemyFixture

from pmg.models import db, House, Committee, CommitteeMeeting  # noqa


class HouseData(DataSet):
    class joint:
        name = 'Joint (NA + NCOP)'
        name_short = 'Joint'
        sphere = 'national'

    class ncop:
        name = 'National Council of Provinces'
        name_short = 'NCOP'
        sphere = 'national'

    class na:
        name = 'National Assembly'
        name_short = 'NA'
        sphere = 'national'

    class president:
        name = 'The President\'s Office',
        name_short = 'President'
        sphere = 'national'


class CommitteeData(DataSet):
    class communications:
        name = 'Communications'
        house = HouseData.na
        premium = True

    class arts:
        name = 'Arts and Culture'
        house = HouseData.na


class CommitteeMeetingData(DataSet):
    class public:
        date = datetime.datetime(2016, 11, 5, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Public meeting'
        committee = CommitteeData.arts

    class premium_recent:
        date = datetime.datetime(2016, 11, 5, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Premium meeting recent'
        committee = CommitteeData.communications

    class premium_old:
        date = datetime.datetime(2015, 11, 5, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Premium meeting old'
        committee = CommitteeData.communications


dbfixture = SQLAlchemyFixture(
    env=globals(),
    style=NamedDataStyle(),
    engine=db.engine,
    scoped_session=db.Session)
