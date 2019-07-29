import pytz
import datetime
from fixture import DataSet, NamedDataStyle, SQLAlchemyFixture

from pmg.models import (
    db, House, Committee, CommitteeMeeting, Bill, BillType, Province, Party,
    CommitteeMeetingAttendance, Member, CallForComment, TabledCommitteeReport
)

THIS_YEAR = datetime.datetime.today().year


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

    class constitutional_review:
        name = 'Constitutional Review Committee'
        house = HouseData.joint


class CommitteeMeetingData(DataSet):
    class arts_meeting_one:
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Public meeting One'
        committee = CommitteeData.arts

    class arts_meeting_two:
        date = datetime.datetime(2019, 8, 1, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Public meeting Two'
        committee = CommitteeData.arts

    class premium_recent:
        date = datetime.datetime(THIS_YEAR, 11, 5, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Premium meeting recent'
        committee = CommitteeData.communications

    class premium_old:
        date = datetime.datetime(
            THIS_YEAR - 2, 11, 5, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Premium meeting old'
        committee = CommitteeData.communications


class BillTypeData(DataSet):
    class section_74:
        name = "Section 74"
        prefix = "B"
        description = "Section 74"

    class section_77:
        name = "Section 77"
        prefix = "B"
        description = "Section 77"

    class private_member_bill_74:
        name = "Private Member Bill: S74"
        prefix = 'PMB'
        description = 'Private Member Bill: Section 74'

    class private_member_bill_77:
        name = 'Private Member Bill: S77'
        prefix = 'PMB'
        description = 'Private Member Bill: Section 77'


class BillData(DataSet):
    """
    Enter various types of bills
    """

    class food:
        year = 2019
        title = "Food and Health Bill"
        type = BillTypeData.section_74

    class farm:
        year = 2019
        title = 'Farm and Agricultural Bill'
        type = BillTypeData.section_77

    class public:
        year = 2019
        title = 'Public Investment Corporation Amendment Bill'
        type = BillTypeData.private_member_bill_74

    class child:
        year = 2019
        title = "Children's Amendment Bill"
        type = BillTypeData.private_member_bill_77


class CallForCommentData(DataSet):
    class arts_call_for_comment_one:
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        title = 'Feeds and Pet Food Bill - draft'
        committee = CommitteeData.arts
        start_date = datetime.datetime(2019, 1, 30, 0, 0, 0, tzinfo=pytz.utc)
        end_date = datetime.datetime(2019, 4, 30, 0, 0, 0, tzinfo=pytz.utc)
        body = "The Bill seeks to provide for: - regulation of feed and pet food, - regulation of feed ingredients used in the manufacturing of feed and pet food,"
        summary = 'The Department of Agriculture, Forestry and Fisheries has published the draft Feeds and Pet Food Bill, and is asking you to comment.'


class TabledCommitteeReportData(DataSet):
    class arts_tabled_committee_report_one:
        title = 'ATC190710: Report of the Portfolio Committee on Agriculture, Land Reform and Rural Development on the 2019/20 Annual Performance Plan and the Budget of the Department of Agriculture, Forestry and Fisheries (Vote 24) and its Entities, dated 10 July 2019.'
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        committee = CommitteeData.arts
        end_date = datetime.datetime(2019, 4, 30, 0, 0, 0, tzinfo=pytz.utc)
        body = "The Portfolio Committee on Agriculture, Land Reform and Rural Development (hereinafter referred to as the Committee) examined Budget Vote 24: Agriculture, Forestry and Fisheries including the Annual Performance Plan of the Department of Agriculture, Forestry and Fisheries (hereinafter referred to as DAFF or the Department) for the 2019/20 financial year and budget projections for the Medium Term Expenditure Framework (MTEF) period ending in 2021/22."


dbfixture = SQLAlchemyFixture(
    env=globals(),
    style=NamedDataStyle(),
    engine=db.engine,
    scoped_session=db.Session)
