from random import random
import string
import datetime
from dateutil.relativedelta import relativedelta
from dateutil import tz
import logging
import os

from sqlalchemy import desc, Index, func, sql
from sqlalchemy.orm import backref
from sqlalchemy.event import listen
from sqlalchemy import UniqueConstraint

from flask.ext.security import UserMixin, RoleMixin, \
    Security, SQLAlchemyUserDatastore
from flask.ext.sqlalchemy import models_committed
from flask_security import current_user

from werkzeug import secure_filename

from app import app, db
import serializers
from search import Search
from s3_upload import S3Bucket

STATIC_HOST = app.config['STATIC_HOST']

logger = logging.getLogger(__name__)
s3_bucket = S3Bucket()


def allowed_file(filename):
    tmp = '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    logger.debug("File upload for '%s' allowed? %s" % (filename, tmp))
    return tmp


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


def one_year_later():
    return datetime.date.today() + relativedelta(years=1)


class Organisation(db.Model):

    __tablename__ = "organisation"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    paid_subscriber = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)
    # when does this subscription expire?
    expiry = db.Column(db.Date(), default=one_year_later)
    contact = db.Column(db.String(255))

    # premium committee subscriptions
    subscriptions = db.relationship('Committee', secondary='organisation_committee', passive_deletes=True)


    def subscribed_to_committee(self, committee):
        """ Does this organisation have an active subscription to `committee`? """
        return not self.has_expired() and (committee in self.subscriptions)

    def has_expired(self):
        return (self.expiry is not None) and (datetime.date.today() > self.expiry)

    def __unicode__(self):
        return unicode(self.name)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        # send subscriptions back as a dict
        subscription_dict = {}
        if tmp.get('subscriptions'):
            for committee in tmp['subscriptions']:
                subscription_dict[committee['id']] = committee.get('name')
        tmp['subscriptions'] = subscription_dict
        # set 'has_expired' flag as appropriate
        tmp['has_expired'] = self.has_expired()
        return tmp


class User(db.Model, UserMixin):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), default='', server_default='', nullable=False)
    active = db.Column(db.Boolean(), default=True, server_default=sql.expression.true())
    confirmed_at = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    current_login_at = db.Column(db.DateTime(timezone=True))
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    subscribe_daily_schedule = db.Column(db.Boolean(), default=False)
    # when does this subscription expire?
    expiry = db.Column(db.Date(), default=one_year_later)

    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    organisation = db.relationship('Organisation', backref='users', lazy=False, foreign_keys=[organisation_id])

    # premium committee subscriptions, in addition to any that the user's organisation might have
    subscriptions = db.relationship('Committee', secondary='user_committee', passive_deletes=True)

    # alerts for changes to committees
    committee_alerts = db.relationship('Committee', secondary='user_committee_alerts', passive_deletes=True, lazy='joined')
    roles = db.relationship('Role', secondary='roles_users', backref=db.backref('users', lazy='dynamic'))

    def __unicode__(self):
        return unicode(self.email)

    def has_expired(self):
        return (self.expiry is not None) and (datetime.date.today() > self.expiry)

    def update_current_login(self):
        now = datetime.datetime.utcnow()
        if self.current_login_at + datetime.timedelta(hours=1) < now:
            self.current_login_at = now
            db.session.commit()

    def subscribed_to_committee(self, committee):
        """ Does this user have an active subscription to `committee`? """
        # admin users have access to everything
        if self.has_role('editor'):
            return True

        # inactive users should go away
        if not self.active:
            return False

        # expired users should go away
        if self.has_expired():
            return False

        # first see if this user has a subscription
        if committee in self.subscriptions:
            return True

        # now check if our organisation has access
        return self.organisation and self.organisation.subscribed_to_committee(committee)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp.pop('password')
        tmp.pop('last_login_ip')
        tmp.pop('current_login_ip')
        tmp.pop('last_login_at')
        tmp.pop('current_login_at')
        tmp['confirmed'] = tmp.pop('confirmed_at') is not None
        tmp.pop('login_count')
        tmp['has_expired'] = self.has_expired()

        # send committee alerts back as a dict
        alerts_dict = {}
        if tmp.get('committee_alerts'):
            for committee in tmp['committee_alerts']:
                alerts_dict[committee['id']] = committee.get('name')
        tmp['committee_alerts'] = alerts_dict
        return tmp


def set_organisation(target, value, oldvalue, initiator):
    """Set a user's organisation, based on the domain of their email address."""
    if not target.organisation and value:
        user_domain = value.split("@")[-1]
        org = Organisation.query.filter_by(domain=user_domain).first()
        if org:
            target.organisation = org


# setup listener on User.email attribute
listen(User.email, 'set', set_organisation)


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

organisation_committee = db.Table(
    'organisation_committee',
    db.Column(
        'organisation_id',
        db.Integer(),
        db.ForeignKey('organisation.id', ondelete='CASCADE')),
    db.Column(
        'committee_id',
        db.Integer(),
        db.ForeignKey('committee.id', ondelete='CASCADE')))


user_committee = db.Table(
    'user_committee',
    db.Column(
        'user_id',
        db.Integer(),
        db.ForeignKey('user.id', ondelete="CASCADE")),
    db.Column(
        'committee_id',
        db.Integer(),
        db.ForeignKey('committee.id', ondelete="CASCADE")))


user_committee_alerts = db.Table(
    'user_committee_alerts',
    db.Column(
        'user_id',
        db.Integer(),
        db.ForeignKey('user.id', ondelete="CASCADE")),
    db.Column(
        'committee_id',
        db.Integer(),
        db.ForeignKey('committee.id', ondelete="CASCADE")))


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
    prefix = db.Column(db.String(5))
    description = db.Column(db.Text)

    @classmethod
    def draft(cls):
        return cls.query.filter(cls.name == "Draft").one()

    @classmethod
    def private_member_bill(cls):
        return cls.query.filter(cls.name == "Private Member Bill").one()

    def __unicode__(self):
        return unicode(self.description)


class BillStatus(db.Model):

    __tablename__ = "bill_status"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

    @classmethod
    def current(cls):
        return cls.query.filter(cls.name.in_(["na", "ncop", "president"])).all()

    def __unicode__(self):
        return u'%s (%s)' % (self.description, self.name)


class Bill(db.Model):
    __tablename__ = "bill"
    __table_args__ = (db.UniqueConstraint('number', 'year', 'type_id'), {})

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    number = db.Column(db.Integer)
    year = db.Column(db.Integer, nullable=False)
    date_of_introduction = db.Column(db.Date)
    date_of_assent = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    act_name = db.Column(db.String(250))
    introduced_by = db.Column(db.String(250))

    status_id = db.Column(db.Integer, db.ForeignKey('bill_status.id'))
    status = db.relationship('BillStatus', backref='bill', lazy=False)
    type_id = db.Column(db.Integer, db.ForeignKey('bill_type.id'))
    type = db.relationship('BillType', backref='bill', lazy=False)
    place_of_introduction_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    place_of_introduction = db.relationship('House')
    versions = db.relationship("BillVersion", backref='bill')

    @property
    def code(self):
        out = self.type.prefix if self.type else "X"
        out += str(self.number) if self.number else ""
        out += "-" + str(self.year)
        return unicode(out)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp['code'] = self.code
        return tmp

    def __unicode__(self):
        out = self.code
        if self.title:
            out += " - " + self.title
        return unicode(out)


class BillVersion(db.Model):
    __tablename__ = "bill_versions"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date(), nullable=False)
    title = db.Column(db.String(), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete='CASCADE'))
    file = db.relationship('File', backref='bill_version', lazy=False)


class File(db.Model):

    __tablename__ = "file"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250))
    file_mime = db.Column(db.String(100))
    origname = db.Column(db.String(255))
    description = db.Column(db.String(255))
    duration = db.Column(db.Integer, default=0)
    playtime = db.Column(db.String(10))
    file_path = db.Column(db.String(255))

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp['url'] = self.file_url
        return tmp

    @property
    def file_url(self):
        return STATIC_HOST + self.file_path

    def from_upload(self, file_data):
        """ Handle a POST-based file upload and use it as the content for this file. """
        if not allowed_file(file_data.filename):
            raise Exception("File type not allowed.")

        # save file to disk
        filename = secure_filename(file_data.filename)
        logger.debug('saving uploaded file: ' + filename)
        file_data.save(os.path.join(app.config['UPLOAD_PATH'], filename))

        # upload saved file to S3
        self.file_path = s3_bucket.upload_file(filename)
        self.file_mime = file_data.mimetype


    def __unicode__(self):
        return u'%s' % self.file_path



class Event(db.Model):
    """ An event is a generic model which represents an event that took
    place at a certain time and may have rich content associated with it.

    An event can have an arbitrary amount of content associated with it
    through associations with the Content model. In turn, a Content
    instance can have multiple files attached to it, and optional
    body and summary text.
    """

    __tablename__ = "event"
    __mapper_args__ = {
        'polymorphic_on': 'type'
    }

    id = db.Column(db.Integer, index=True, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), nullable=False)
    title = db.Column(db.String(256))
    type = db.Column(db.String(50), index=True, nullable=False)
    nid = db.Column(db.Integer())

    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), index=True)
    member = db.relationship('Member', backref='events')
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete='SET NULL'), index=True)
    committee = db.relationship('Committee', lazy=False, backref=backref( 'events', order_by=desc('Event.date')))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), index=True)
    house = db.relationship('House', lazy=False, backref=backref( 'events', order_by=desc('Event.date')))
    bills = db.relationship('Bill', secondary='event_bills', backref=backref('events'))

    featured = db.Column(db.Boolean(), default=False, server_default=sql.expression.false(), nullable=False, index=True)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        return tmp

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


event_bills = db.Table(
    'event_bills',
    db.Column('event_id', db.Integer(), db.ForeignKey('event.id')),
    db.Column('bill_id', db.Integer(), db.ForeignKey('bill.id')))


class WithBodyContent(object):
    """ Mixin that will find the first associated Content object
    that has a body or summary attribute, and delegate to it. """
    @property
    def content_body(self):
        for c in self.content:
            if c.body:
                return c.body

    @property
    def content_summary(self):
        for c in self.content:
            if c.summary:
                return c.summary


class CommitteeMeeting(WithBodyContent, Event):
    __mapper_args__ = {
        'polymorphic_identity': 'committee-meeting'
    }
    chairperson = db.Column(db.String(256))

    def check_permission(self):
        # by default, all committee meetings are accessible
        if self.committee and self.committee.premium:
            if not current_user.is_authenticated():
                return False

            return current_user.subscribed_to_committee(self.committee)
        return True

    def to_dict(self, include_related=False):
        tmp = super(CommitteeMeeting, self).to_dict(include_related=include_related)
        # check user permissions, popping some content if required
        if not self.check_permission():
            if tmp['content']:
                # remove premium content
                tmp['premium_content_excluded'] = True
                tmp['content'] = []
        return tmp


class Hansard(WithBodyContent, Event):
    __mapper_args__ = {
        'polymorphic_identity': 'plenary'
    }


class Briefing(WithBodyContent, Event):
    __mapper_args__ = {
        'polymorphic_identity': 'media-briefing'
    }


class BillIntroduction(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-introduced'
    }


class BillAdoption(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-passed'
    }


class BillApproval(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-signed'
    }


class BillEnactment(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-enacted'
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
    # is this person *currently* an MP?
    current = db.Column(db.Boolean, default=True, server_default=sql.expression.true(), nullable=False, index=True)

    memberships = db.relationship('Membership', backref=backref("member", lazy="joined"), lazy='joined')

    def __unicode__(self):
        return u'%s' % self.name

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)

        if tmp['profile_pic_url']:
            tmp['profile_pic_url'] = STATIC_HOST + tmp['profile_pic_url']

        if tmp['pa_link']:
            link = tmp['pa_link']
            if not link.startswith('http://'):
                link = 'http://www.pa.org.za' + link
            tmp['pa_url'] = link

        return tmp


class Committee(db.Model):

    __tablename__ = "committee"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    about = db.Column(db.Text())
    contact_details = db.Column(db.Text())
    ad_hoc = db.Column(db.Boolean())
    premium = db.Column(db.Boolean())

    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    house = db.relationship('House', lazy='joined')

    memberships = db.relationship('Membership', backref="committee", cascade='all, delete-orphan', passive_deletes=True)

    @classmethod
    def premium_for_select(cls):
        return cls.query.filter(cls.premium == True)\
                .order_by(cls.name)\
                .all()

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
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="CASCADE"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)

    def __unicode__(self):
        tmp = u" - ".join([unicode(self.type),
                           unicode(self.member),
                           unicode(self.committee)])
        return unicode(tmp)


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
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship(
        'Committee',
        backref=db.backref('questions_replies'))
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    body = db.Column(db.Text)
    question_number = db.Column(db.String(255))
    nid = db.Column(db.Integer())


# === Tabled Committee Report === #

class TabledCommitteeReport(db.Model):

    __tablename__ = "tabled_committee_report"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    body = db.Column(db.Text())
    summary = db.Column(db.Text())
    nid = db.Column(db.Integer())

    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship(
        'Committee',
        backref=db.backref('tabled_committee_reports'))
    files = db.relationship(
        "File",
        secondary='tabled_committee_report_file_join', backref='tabled_committee_report')

    def __unicode__(self):
        return self.title or ('<TabledCommitteeReport %s>' % self.id)

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
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship(
        'Committee',
        backref=db.backref('calls_for_comments'))
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
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())


    files = db.relationship("File", secondary='policy_document_file_join', backref='policy_document')

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
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())

    files = db.relationship("File", secondary='gazette_file_join', backref="gazette")

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


# === Featured Content === #

class Featured(db.Model):

    __tablename__ = "featured"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    blurb = db.Column(db.Text())
    link = db.Column(db.String(255))
    start_date = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)
    tabled_committee_report = db.relationship(
        'TabledCommitteeReport',
        secondary='featured_tabled_committee_report_join')

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
    files = db.relationship("File", secondary='daily_schedule_file_join', backref='daily_schedule')

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


class Content(db.Model):

    __tablename__ = "content"

    id = db.Column(db.Integer, index=True, primary_key=True)
    type = db.Column(db.String(50), index=True, nullable=False)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), index=True)
    event = db.relationship('Event', backref=backref('content', lazy='joined'))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), index=True)
    file = db.relationship('File', lazy='joined')

    # optional HTML summary and body of this content
    summary = db.Column(db.Text())
    body = db.Column(db.Text())

    def __unicode__(self):
        return unicode(self.type + " - " + str(self.id))

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        # lift nested 'file' fields to look like attributes on this model
        if tmp.get('file'):
            for key, val in tmp['file'].iteritems():
                if tmp.get(key):
                    pass  # don't overwrite parent model attributes from the child model
                tmp[key] = val
            tmp.pop('file')
        return tmp


class HitLog(db.Model):

    __tablename__ = "hit_log"

    id = db.Column(db.Integer, index=True, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.datetime.utcnow)
    ip_addr = db.Column(db.String(40), index=True)
    user_agent = db.Column(db.String(255))
    url = db.Column(db.String(255))



class EmailTemplate(db.Model):
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1024))
    subject = db.Column(db.String(100))
    body = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())



# Listen for model updates
@models_committed.connect_via(app)
def on_models_changed(sender, changes):
    searcher = Search()

    for obj, change in changes:
        # obj is the changed object, change is one of: update, insert, delete

        if searcher.indexable(obj):
            logger.debug('Reindexing changed item: %s %s' % (change, obj))

            if change == 'delete':
                # deleted
                searcher.delete_obj(obj)
            else:
                # updated or inserted
                searcher.add_obj(obj)


class Redirect(db.Model):
    __tablename__ = 'redirect'

    id = db.Column(db.Integer, primary_key=True)
    nid = db.Column(db.Integer)
    old_url = db.Column(db.String(250), nullable=False, unique=True, index=True)
    new_url = db.Column(db.String(250))

    def __str__(self):
        if self.nid:
            target = "nid %s" % self.nid
        else:
            target = self.new_url

        return u'<Redirect from %s to %s>' % (self.old_url, target)
