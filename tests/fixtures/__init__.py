import pytz
import datetime
from fixture import DataSet, NamedDataStyle, SQLAlchemyFixture

from pmg.models import (
    db, House, Committee, CommitteeMeeting, Bill, BillType, Province, Party,
    CommitteeMeetingAttendance, Member, CallForComment, TabledCommitteeReport,
    CommitteeQuestion, Minister, Event, Featured, Page, BillStatus, Post, User,
    Role, Membership, MembershipType
)

THIS_YEAR = datetime.datetime.today().year


class HouseData(DataSet):
    class joint:
        id = 1
        name = 'Joint (NA + NCOP)'
        name_short = 'Joint'
        sphere = 'national'

    class ncop:
        id = 2
        name = 'National Council of Provinces'
        name_short = 'NCOP'
        sphere = 'national'

    class na:
        id = 3
        name = 'National Assembly'
        name_short = 'NA'
        sphere = 'national'

    class president:
        id = 4
        name = 'The President\'s Office',
        name_short = 'President'
        sphere = 'national'

class MinisterData(DataSet):
    class minister_of_arts:
        name = "Minister of Sports, Arts and Culture"

class CommitteeData(DataSet):
    class communications:
        name = 'Communications'
        house = HouseData.na
        premium = True

    class arts:
        name = 'Arts and Culture'
        house = HouseData.na
        minister = MinisterData.minister_of_arts

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
        featured = True

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
        
    class section_75:
        name = "Section 75"
        prefix = "B"
        description = "Ordinary Bills not affecting the provinces"

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


class BillStatusData(DataSet):
    class current:
        name = "na"
        description = "current"

class BillData(DataSet):
    """
    Enter various types of bills
    """

    class food:
        year = 2019
        title = "Food and Health Bill"
        type = BillTypeData.section_74
        introduced_by = "Minister of Finance"
        status = BillStatusData.current

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

    class sport:
        year = 2019
        title = "2010 FIFA World Cup South Africa Special Measures Bill"
        type = BillTypeData.section_75

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

class PartyData(DataSet):
    class da:
        name = "Democratic Alliance (DA)"
    class anc:
        name = "African National Congress (ANC)"

class ProvinceData(DataSet):
    class western_cape:
        name = "Western Cape"
    class gauteng:
        name = "Gauteng"

class MemberData(DataSet):
    class veronica:
        name = "Ms Veronica Van Dyk"
        profile_pic_url = "https://www.pa.org.za/media_root/cache/02/93/0293cce7701daf86fa88fe02e1db9c58.jpg"
        bio = "Ms Veronica van Dyk is the Deputy Shadow Minister for Communications in the DA, since June 2014. She is a former Ward Councillor of the Nama Khoi Local Municipality."
        house = HouseData.na 
        party = PartyData.da
        province = ProvinceData.western_cape
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        pa_link = "http://www.pa.org.za"
        current = True
    class not_current_member:
        name = "Phoebe Noxolo Abraham"
        house = HouseData.na 
        party = PartyData.anc
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        current = False
    class laetitia:
        name = "Laetitia Heloise Arries"
        house = HouseData.joint
        party = PartyData.anc
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        current = True

class CommitteeQuestionData(DataSet):
    class arts_committee_question_one:
        minister = MinisterData.minister_of_arts
        code = "NA1"
        question_number = 1
        house = HouseData.na
        written_number = 1
        oral_number = 1
        answer_type = "oral"
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        year = 2019
        question = "What programmes that promote the languages, culture and heritage of the Khoi and San has the Government implemented in each province in each of the past five years" 
        answer = "Through possible funding and strategic partnerships between PanSALB and my Department, PanSALB was able to initiate and support the following programmes."
        question_to_name = "Minister of Sports, Arts and Culture"
        intro = "Van Dyk, Ms V to ask the Minister of Sports, Arts and Culture:"
        asked_by_name = "Van Dyk, Ms V"
        asked_by_member = MemberData.veronica

class EventData(DataSet):
    class arts_bill_event:
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        title = "2010 FIFA World Cup South Africa Special Measures Bill [B13-2006]: Department briefing"
        type = "Meeting"
        committee = CommitteeData.arts
        house = HouseData.na
        bills = [BillData.sport]

class FeaturedData(DataSet):
    class the_week_ahead:
        title = "The Week Ahead: End of the First Term"
        link = "https://pmg.org.za/blog/The%20Week%20Ahead:%20End%20of%20the%20First%20Term"
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)

    class current_bills:
        title = "Current Bills"
        start_date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        link = "https://pmg.org.za/bills/current/"

class PageData(DataSet):
    class section_25_review_process:
        title = "Section 25 review process"
        slug = "Section25reviewprocess" 
        body = "In February 2018, the National Assembly adopted a motion proposed by the EFF, with amendments by the ANC that Parliament's Constitutional Review Committee investigates mechanisms through which land can be expropriated without compensation."
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        featured = True
    class un_featured_page:
        title = "Unfeatured page"
        slug = "unfeaturedpage" 
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        featured = False

class PostData(DataSet):
    class the_week_ahead:
        title = "The Week Ahead: End of the First Term"
        slug = "theweekahead" 
        featured = True
        body = "A lot was packed into the first term of the Sixth Parliament."
        date = datetime.datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.utc)

class RoleData(DataSet):
    class admin:
        name = "user-admin"
        description = "user-admin"
    class editor:
        name = "editor"
        description = "editor"

class UserData(DataSet):
    class admin:
        email = "admin@pmg.org.za"
        name = "Admin User"
        active = True
        roles = [RoleData.admin, RoleData.editor]
        current_login_at = datetime.datetime.utcnow()
        confirmed = True

class MembershipTypeData(DataSet):
    class member:
        name = "Member"

class MembershipData(DataSet):
    class arts_membership_one:
        type = MembershipTypeData.member
        committee = CommitteeData.arts
        member = MemberData.veronica



dbfixture = SQLAlchemyFixture(
    env=globals(),
    style=NamedDataStyle(),
    engine=db.engine,
    scoped_session=db.Session)
