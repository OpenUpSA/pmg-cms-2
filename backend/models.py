from random import random
import string
import datetime
import logging

from sqlalchemy import desc, Index
from sqlalchemy.orm import backref
from sqlalchemy import UniqueConstraint

from flask.ext.security import UserMixin, RoleMixin, \
    Security, SQLAlchemyUserDatastore

from app import app, db
import serializers

STATIC_HOST = app.config['STATIC_HOST']

logger = logging.getLogger(__name__)


class ApiKey(db.Model):

    __tablename__ = "api_key"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        unique=True,
        nullable=False)
    user = db.relationship('User')

    def generate_key(self):
        self.key = ''.join(
            random.choice(
                string.ascii_uppercase +
                string.digits) for _ in range(128))
        return

    def __unicode__(self):
        s = u'%s' % self.key
        return s

    def to_dict(self, include_related=False):
        return {'user_id': self.user_id, 'key': self.key}


class Role(db.Model, RoleMixin):

    __tablename__ = "role"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __unicode__(self):
        return unicode(self.name)


class User(db.Model, UserMixin):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)

    roles = db.relationship('Role', secondary='roles_users',
                            backref=db.backref('users', lazy='dynamic'))

    def __unicode__(self):
        return unicode(self.email)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp.pop('password')
        tmp.pop('last_login_ip')
        tmp.pop('current_login_ip')
        tmp.pop('last_login_at')
        tmp.pop('current_login_at')
        tmp.pop('confirmed_at')
        tmp.pop('login_count')
        return tmp

roles_users = db.Table(
    'roles_users',
    db.Column(
        'user_id',
        db.Integer(),
        db.ForeignKey('user.id')),
    db.Column(
        'role_id',
        db.Integer(),
        db.ForeignKey('role.id')))

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


class House(db.Model):

    __tablename__ = "house"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    name_short = db.Column(db.String(20), nullable=False)

    def __unicode__(self):
        return unicode(self.name)


class Party(db.Model):

    __tablename__ = "party"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def __unicode__(self):
        return unicode(self.name)


class Province(db.Model):

    __tablename__ = "province"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def __unicode__(self):
        return unicode(self.name)


class BillType(db.Model):

    __tablename__ = "bill_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __unicode__(self):
        return unicode(self.name)


class BillStatus(db.Model):

    __tablename__ = "bill_status"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __unicode__(self):
        return unicode(self.name)


class Bill(db.Model):

    __tablename__ = "bill"
    __table_args__ = (
        db.UniqueConstraint(
            'number',
            'year',
            'bill_type_id',
            'title'),
        {})

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    bill_code = db.Column(db.String(100))
    act_name = db.Column(db.String(250))
    number = db.Column(db.Integer)
    year = db.Column(db.Integer)
    date_of_introduction = db.Column(db.Date)
    date_of_assent = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    objective = db.Column(db.String(1000))
    is_deleted = db.Column(db.Boolean, default=False)

    status_id = db.Column(db.Integer, db.ForeignKey('bill_status.id'))
    status = db.relationship('BillStatus', backref='bill', lazy=False)
    bill_type_id = db.Column(db.Integer, db.ForeignKey('bill_type.id'))
    bill_type = db.relationship('BillType', backref='bill', lazy=False)
    place_of_introduction_id = db.Column(
        db.Integer,
        db.ForeignKey('committee.id'))
    place_of_introduction = db.relationship('Committee')
    introduced_by_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    introduced_by = db.relationship('Member')

    file_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    files = db.relationship("File")

    def code(self):
        return self.type.prefix + str(self.number) + "-" + str(self.year)

    def delete(self):
        self.is_deleted = True

    def __unicode__(self):
        return unicode(str(self.code) + " - " + self.name)


class Briefing(db.Model):

    __tablename__ = "briefing"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    briefing_date = db.Column(db.Date)
    summary = db.Column(db.Text)
    minutes = db.Column(db.Text)
    presentation = db.Column(db.Text)
    files = db.relationship("File", secondary='briefing_file_join')
    start_date = db.Column(db.Date())

briefing_file_table = db.Table(
    'briefing_file_join',
    db.Model.metadata,
    db.Column(
        'briefing_id',
        db.Integer,
        db.ForeignKey('briefing.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')))


class File(db.Model):

    __tablename__ = "file"

    id = db.Column(db.Integer, primary_key=True)
    filemime = db.Column(db.String(50))
    origname = db.Column(db.String(255))
    description = db.Column(db.String(255))
    duration = db.Column(db.Integer, default=0)
    playtime = db.Column(db.String(10))
    url = db.Column(db.String(255))

    def __unicode__(self):
        return u'%s' % self.url

# M2M table
bill_event_table = db.Table(
    'bill_event', db.Model.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id'))
)


class Event(db.Model):

    __tablename__ = "event"

    id = db.Column(db.Integer, index=True, primary_key=True)
    date = db.Column(db.DateTime)
    title = db.Column(db.String(256))
    type = db.Column(db.String(50), index=True, nullable=False)

    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), index=True)
    member = db.relationship('Member', backref='events')
    committee_id = db.Column(
        db.Integer,
        db.ForeignKey('committee.id'),
        index=True)
    committee = db.relationship(
        'Committee',
        lazy=False,
        backref=backref(
            'events',
            order_by=desc('Event.date')))

    def __unicode__(self):
        if self.type == "committee-meeting":
            tmp = "unknown date"
            if self.date:
                tmp = self.date.date().isoformat()
            if self.committee:
                tmp += " [" + unicode(self.committee) + "]"
            if self.title:
                tmp += " - " + self.title
            return unicode(tmp)
        tmp = self.type
        if self.date:
            tmp += " - " + self.date.date().isoformat()
        if self.title:
            tmp += " - " + self.title
        return unicode(tmp)

    __mapper_args__ = {
        'polymorphic_identity': 'event',
        'polymorphic_on': type,
    }


class MembershipType(db.Model):

    __tablename__ = "membership_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self, include_related=False):
        # reduce this model to a string
        return self.name

    def __unicode__(self):
        return unicode(self.name)


class Member(db.Model):

    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_pic_url = db.Column(db.String(255))
    bio = db.Column(db.Text())
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    house = db.relationship(House)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'))
    party = db.relationship(Party, backref="members", lazy='joined')
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'))
    province = db.relationship(Province)
    start_date = db.Column(db.Date())
    pa_link = db.Column(db.String(255))

    def __unicode__(self):
        return u'%s' % self.name

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        if tmp['profile_pic_url']:
            tmp['profile_pic_url'] = STATIC_HOST + tmp['profile_pic_url']
        logger.debug(STATIC_HOST)
        return tmp


class Committee(db.Model):

    __tablename__ = "committee"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    about = db.Column(db.Text())
    contact_details = db.Column(db.Text())

    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    house = db.relationship('House', lazy='joined')

    tabled_committee_reports = db.relationship(
        "TabledCommitteeReport",
        lazy=True)
    questions_replies = db.relationship("QuestionReply", lazy=True)
    calls_for_comment = db.relationship("CallForComment", lazy=True)

    def __unicode__(self):
        tmp = self.name
        if self.house:
            tmp = self.house.name_short + " " + tmp
        return unicode(tmp)


class Membership(db.Model):

    __tablename__ = 'committee_members'

    id = db.Column(db.Integer, primary_key=True)

    type_id = db.Column(db.Integer, db.ForeignKey('membership_type.id'))
    type = db.relationship(MembershipType, lazy='joined')
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id'))
    committee = db.relationship(
        Committee,
        backref="memberships",
        lazy='joined')
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    member = db.relationship(
        Member,
        backref=backref(
            "memberships",
            lazy="joined"),
        lazy='joined')

    def __unicode__(self):
        tmp = u" - ".join([unicode(self.type),
                           unicode(self.member),
                           unicode(self.committee)])
        return unicode(tmp)


class Hansard(db.Model):

    __tablename__ = "hansard"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    meeting_date = db.Column(db.Date())
    start_date = db.Column(db.Date())
    body = db.Column(db.Text())


# === Schedule === #

class Schedule(db.Model):

    __tablename__ = "schedule"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    meeting_date = db.Column(db.Date())
    meeting_time = db.Column(db.Text())
    houses = db.relationship("House", secondary='schedule_house_join')

schedule_house_table = db.Table(
    'schedule_house_join', db.Model.metadata,
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id')),
    db.Column('house_id', db.Integer, db.ForeignKey('house.id'))
)


# === Questions Replies === #

class QuestionReply(db.Model):

    __tablename__ = "question_reply"

    id = db.Column(db.Integer, primary_key=True)
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id'))
    committee = db.relationship(
        'Committee',
        backref=db.backref(
            'question-replies-committee',
            lazy='dynamic'))
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    body = db.Column(db.Text)
    question_number = db.Column(db.String(255))


# === Tabled Committee Report === #

class TabledCommitteeReport(db.Model):

    __tablename__ = "tabled_committee_report"

    id = db.Column(db.Integer, primary_key=True)
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id'))
    committee = db.relationship(
        'Committee',
        backref=db.backref(
            'committee',
            lazy='dynamic'))
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    body = db.Column(db.Text())
    summary = db.Column(db.Text())
    nid = db.Column(db.Integer())
    files = db.relationship(
        "File",
        secondary='tabled_committee_report_file_join')

tabled_committee_report_file_table = db.Table(
    'tabled_committee_report_file_join',
    db.Model.metadata,
    db.Column(
        'tabled_committee_report_id',
        db.Integer,
        db.ForeignKey('tabled_committee_report.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')))


# === Calls for comment === #

class CallForComment(db.Model):

    __tablename__ = "call_for_comment"

    id = db.Column(db.Integer, primary_key=True)
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id'))
    committee = db.relationship(
        'Committee',
        backref=db.backref(
            'call-for-comment-committee',
            lazy='dynamic'))
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    body = db.Column(db.Text())
    summary = db.Column(db.Text())
    nid = db.Column(db.Integer())


# === Policy document === #

class PolicyDocument(db.Model):

    __tablename__ = "policy_document"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    effective_date = db.Column(db.Date())
    files = db.relationship("File", secondary='policy_document_file_join')
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())

policy_document_file_table = db.Table(
    'policy_document_file_join',
    db.Model.metadata,
    db.Column(
        'policy_document_id',
        db.Integer,
        db.ForeignKey('policy_document.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')),
)


# === Gazette === #

class Gazette(db.Model):

    __tablename__ = "gazette"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    effective_date = db.Column(db.Date())
    files = db.relationship("File", secondary='gazette_file_join')
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())

gazette_file_table = db.Table(
    'gazette_file_join',
    db.Model.metadata,
    db.Column(
        'gazette_id',
        db.Integer,
        db.ForeignKey('gazette.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')))


# === Book === #

class Book(db.Model):

    __tablename__ = "book"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text())
    body = db.Column(db.Text())
    start_date = db.Column(db.Date())
    files = db.relationship("File", secondary='book_file_join')
    nid = db.Column('nid', db.Integer())

book_file_table = db.Table(
    'book_file_join',
    db.Model.metadata,
    db.Column(
        'book_id',
        db.Integer,
        db.ForeignKey('book.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')))


# === Featured Content === #

class Featured(db.Model):

    __tablename__ = "featured"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    blurb = db.Column(db.Text())
    link = db.Column(db.String(255))
    start_date = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    committee_meeting = db.relationship(
        'CommitteeMeeting',
        secondary='featured_committee_meeting_join')
    tabled_committee_report = db.relationship(
        'TabledCommitteeReport',
        secondary='featured_tabled_committee_report_join')

featured_committee_meeting_join = db.Table(
    'featured_committee_meeting_join',
    db.Model.metadata,
    db.Column(
        'featured_id',
        db.Integer,
        db.ForeignKey('featured.id')),
    db.Column(
        'committee_meeting_id',
        db.Integer,
        db.ForeignKey('committee_meeting.id')))

featured_tabled_committee_report_join = db.Table(
    'featured_tabled_committee_report_join',
    db.Model.metadata,
    db.Column(
        'featured_id',
        db.Integer,
        db.ForeignKey('featured.id')),
    db.Column(
        'tabled_committee_report_id',
        db.Integer,
        db.ForeignKey('tabled_committee_report.id')))

# === Daily schedules === #


class DailySchedule(db.Model):

    __tablename__ = "daily_schedule"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    schedule_date = db.Column(db.Date())
    body = db.Column(db.Text())
    nid = db.Column(db.Integer())
    files = db.relationship("File", secondary='daily_schedule_file_join')

daily_schedule_file_table = db.Table(
    'daily_schedule_file_join',
    db.Model.metadata,
    db.Column(
        'daily_schedule_id',
        db.Integer,
        db.ForeignKey('daily_schedule.id')),
    db.Column(
        'file_id',
        db.Integer,
        db.ForeignKey('file.id')))


class CommitteeMeeting(Event):

    __tablename__ = "committee_meeting"

    id = db.Column(db.Integer, index=True, primary_key=True)

    body = db.Column(db.Text())
    summary = db.Column(db.Text())

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), index=True)

    def __unicode__(self):
        return unicode(self.id)

    __mapper_args__ = {
        'polymorphic_identity': 'committee-meeting',
    }


class Content(db.Model):

    __tablename__ = "content"

    id = db.Column(db.Integer, index=True, primary_key=True)
    type = db.Column(db.String(50), index=True, nullable=False)
    title = db.Column(db.String(200))
    file_path = db.Column(db.String(200))

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), index=True)
    event = db.relationship('Event', backref=backref('content', lazy='joined'))

    def __unicode__(self):
        return unicode(self.title)


class HitLog(db.Model):

    __tablename__ = "hit_log"

    id = db.Column(db.Integer, index=True, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ip_addr = db.Column(db.String(40), index=True)
    user_agent = db.Column(db.String(255))
    url = db.Column(db.String(255))
