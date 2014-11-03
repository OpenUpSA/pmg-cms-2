from app import app, db, logger
import serializers
from sqlalchemy import desc
from sqlalchemy.orm import backref
from sqlalchemy import UniqueConstraint
from random import random
import string
from passlib.apps import custom_app_context as pwd_context


class ApiKey(db.Model):

    __tablename__ = "api_key"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    user = db.relationship('User')

    def generate_key(self):
        self.key=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(128))
        return

    def __unicode__(self):
        s = u'%s' % self.key
        return s

    def to_dict(self, include_related=False):
        return {'user_id': self.user_id, 'key': self.key}


class User(db.Model):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    activated = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def is_active(self):
        return self.activated

    def __unicode__(self):
        s = u'%s' % self.email
        return s

    def to_dict(self, include_related=False):
        return serializers.user_to_dict(self)


class BillType(db.Model):

    __tablename__ = "bill_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    prefix = db.Column(db.String(10), nullable=False)

    def __unicode__(self):
        return u'%s' % self.name


class BillStatus(db.Model):

    __tablename__ = "bill_status"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __unicode__(self):
        return u'%s' % self.name


class Bill(db.Model):

    __tablename__ = "bill"

    __table_args__ = (db.UniqueConstraint('number', 'year', 'type_id', 'name'), {})
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    code = db.Column(db.String(100))
    act_name = db.Column(db.String(250))
    number = db.Column(db.Integer)
    year = db.Column(db.Integer)
    date_of_introduction = db.Column(db.Date)
    date_of_assent = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    objective = db.Column(db.String(1000))
    is_deleted = db.Column(db.Boolean, default=False)

    status_id = db.Column(db.Integer, db.ForeignKey('bill_status.id'))
    status = db.relationship('BillStatus', backref='bills')
    type_id = db.Column(db.Integer, db.ForeignKey('bill_type.id'))
    type = db.relationship('BillType', backref='bills')
    place_of_introduction_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    place_of_introduction = db.relationship('Organisation')
    introduced_by_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    introduced_by = db.relationship('Member')

    files = db.relationship('BillFile')

    def code(self):
        return self.type.prefix + str(self.number) + "-" + str(self.year)

    def delete(self):
        self.is_deleted = True

    def __str__(self):
        return str(self.code) + " - " + self.name

    def __repr__(self):
        return '<Bill: %r>' % str(self)

class BillFile(db.Model):
    __tablename__ = "file"
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
    filemime = db.Column(db.String(50))
    origname = db.Column(db.String(255))
    description = db.Column(db.String(255))
    duration = db.Column(db.Integer, default = 0)
    url = db.Column(db.String(255))

    def __unicode__(self):
        return u'%s' % self.url

# M2M table
bill_event_table = db.Table(
    'bill_event', db.Model.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id'))
)


class EventType(db.Model):

    __tablename__ = "event_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self, include_related=False):
        # reduce this model to a string
        return self.name

    def __unicode__(self):
        return u'%s' % self.name


class Event(db.Model):
    __tablename__ = "event"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    title = db.Column(db.String(250))

    event_type_id = db.Column(db.Integer, db.ForeignKey('event_type.id'))
    type = db.relationship('EventType', lazy='joined')
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    member = db.relationship('Member', backref='events')
    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    organisation = db.relationship('Organisation', backref=backref('events', order_by=desc('Event.date')))

    def __unicode__(self):
        return u'%s' % self.name


class MembershipType(db.Model):

    __tablename__ = "membership_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self, include_related=False):
        # reduce this model to a string
        return self.name

    def __unicode__(self):
        return u'%s' % self.name


class Member(db.Model):

    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_pic_url = db.Column(db.String(200))
    bio = db.Column(db.String(1500))
    version = db.Column(db.Integer, nullable=False)

    def __unicode__(self):
        return u'%s' % self.name


class Organisation(db.Model):

    __tablename__ = "organisation"

    __table_args__ = (db.UniqueConstraint('name', 'type'), {})
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    version = db.Column(db.Integer, nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    parent = db.relationship('Organisation', uselist=False, remote_side=[id], lazy='joined', join_depth=1)

    to_dict = serializers.organisation_to_dict

    def __unicode__(self):
        return u'%s' % self.name


class Membership(db.Model):
    __tablename__ = 'organisation_members'

    id = db.Column(db.Integer, primary_key=True)

    type_id = db.Column(db.Integer, db.ForeignKey('membership_type.id'))
    type = db.relationship(MembershipType, lazy='joined')
    organisation_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    organisation = db.relationship(Organisation, backref="memberships", lazy='joined')
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    member = db.relationship(Member, backref=backref("memberships", lazy="joined"), lazy='joined')


class CommitteeInfo(db.Model):

    __tablename__ = "committee_info"

    id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.String(1500))
    contact_details = db.Column(db.String(1500))

    organization_id = db.Column(db.Integer, db.ForeignKey('organisation.id'), nullable=False)
    organization = db.relationship('Organisation', backref=backref('info', lazy='joined', uselist=False))

    def __unicode__(self):
        return u'%s' % self.about


class Content(db.Model):

    __tablename__ = "content"
    # __table_args__ = (db.UniqueConstraint('type', 'title', 'file_path', 'event_id', 'version'), {})

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200))
    file_path = db.Column(db.String(200))
    body = db.Column(db.String(20000))
    summary = db.Column(db.String(5000))
    version = db.Column(db.Integer, nullable=False)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', backref='content')

    def __unicode__(self):
        return u'%s' % self.title

