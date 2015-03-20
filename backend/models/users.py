from random import random
import string
import datetime
from dateutil.relativedelta import relativedelta

from sqlalchemy import desc, Index, func, sql
from sqlalchemy.orm import backref, validates, joinedload
from sqlalchemy.event import listen
from sqlalchemy import UniqueConstraint

from flask.ext.security import UserMixin, RoleMixin, Security, SQLAlchemyUserDatastore

from frontend import app, db
import backend.serializers as serializers

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

    def gets_alerts_for(self, committee):
        from ..models.resources import Committee
        if not isinstance(committee, Committee):
            committee = Committee.query.get(committee)
        return committee in self.committee_alerts

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
