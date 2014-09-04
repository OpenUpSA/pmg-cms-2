from app import app, db, logger
import serializers
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
        return u'%s' % self.value


class BillStatus(db.Model):

    __tablename__ = "bill_status"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __unicode__(self):
        return u'%s' % self.value


class Bill(db.Model):

    __tablename__ = "bill"

    __table_args__ = (db.UniqueConstraint('number', 'year', 'type_id', 'name'), {})
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    act_name = db.Column(db.String(250))
    number = db.Column(db.Integer)
    year = db.Column(db.Integer)
    date_of_introduction = db.Column(db.Date)
    date_of_assent = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    objective = db.Column(db.String(1000))
    is_deleted = db.Column(db.Boolean, default=False)

    status_id = db.Column(db.Integer, db.ForeignKey('bill_status.id'), nullable=False)
    status = db.relationship('BillStatus', backref='bills')
    type_id = db.Column(db.Integer, db.ForeignKey('bill_type.id'), nullable=False)
    type = db.relationship('BillType', backref='bills')
    place_of_introduction_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    place_of_introduction = db.relationship('Location', backref='bills_introduced')
    introduced_by_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    introduced_by = db.relationship('Member', backref='bills_introduced')

    def code(self):
        return self.type.prefix + str(self.number) + "-" + str(self.year)

    def delete(self):
        self.is_deleted = True

    def __str__(self):
        return str(self.code) + " - " + self.name

    def __repr__(self):
        return '<Bill: %r>' % str(self)


# M2M table
bill_event_table = db.Table(
    'bill_event', db.Model.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id'))
)


class Event(db.Model):

    __tablename__ = "event"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date)

    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    content = db.relationship('Content', backref='event')
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    location = db.relationship('Location', backref='events')

    def __unicode__(self):
        return u'%s' % self.value


class Location(db.Model):

    __tablename__ = "location"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __unicode__(self):
        return u'%s' % self.value


# M2M table
membership_table = db.Table(
    'member_organisation', db.Model.metadata,
    db.Column('member_id', db.Integer, db.ForeignKey('member.id'), primary_key=True),
    db.Column('organisation_id', db.Integer, db.ForeignKey('organisation.id'), primary_key=True)
)


class Member(db.Model):

    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_pic_url = db.Column(db.String(200))
    bio = db.Column(db.String(1500))
    version = db.Column(db.Integer, nullable=False)

    memberships = db.relationship("Organisation",
                    secondary=membership_table,
                    backref="followed_by"
    )

    def __unicode__(self):
        return u'%s' % self.value


class Organisation(db.Model):

    __tablename__ = "organisation"

    __table_args__ = (db.UniqueConstraint('name', 'type', 'location'), {})
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(50), unique=True)
    version = db.Column(db.Integer, nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
    parent = db.relationship('Organisation')

    def __unicode__(self):
        return u'%s' % self.value


class CommitteeInfo(db.Model):

    __tablename__ = "committee_info"

    id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.String(1500))
    contact_details = db.Column(db.String(1500))

    organization_id = db.Column(db.Integer, db.ForeignKey('organisation.id'), nullable=False)
    organization = db.relationship('Organisation', backref='info')

    def __unicode__(self):
        return u'%s' % self.value


class Content(db.Model):

    __tablename__ = "content"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    profile_pic_url = db.Column(db.String(200))
    version = db.Column(db.Integer, nullable=False)

    def __unicode__(self):
        return u'%s' % self.value