from builtins import str
import datetime
from dateutil.relativedelta import relativedelta
from logging import getLogger

from sqlalchemy import sql, event, func, desc
from sqlalchemy.orm import validates

from flask_security import UserMixin, RoleMixin, Security, SQLAlchemyUserDatastore
from flask_security.signals import user_confirmed
from flask import render_template

from flask_mail import Message

from pmg import app, db
from . import serializers
import pmg.forms as forms


log = getLogger(__name__)


class Role(db.Model, RoleMixin):

    __tablename__ = "role"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return str(self.name)


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
    subscriptions = db.relationship(
        "Committee", secondary="organisation_committee", passive_deletes=True
    )

    def subscribed_to_committee(self, committee):
        """ Does this organisation have an active subscription to `committee`? """
        return not self.has_expired() and (committee in self.subscriptions)

    def has_expired(self):
        return (self.expiry is not None) and (datetime.date.today() > self.expiry)

    def __str__(self):
        return str(self.name)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        # send subscriptions back as a dict
        subscription_dict = {}
        if tmp.get("subscriptions"):
            for committee in tmp["subscriptions"]:
                subscription_dict[committee["id"]] = committee.get("name")
        tmp["subscriptions"] = subscription_dict
        # set 'has_expired' flag as appropriate
        tmp["has_expired"] = self.has_expired()
        return tmp


@event.listens_for(Organisation.expiry, "set")
def organisation_expiry_set(target, value, oldvalue, initiator):
    for user in target.users:
        user.expiry = value


class User(db.Model, UserMixin):

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), default="", server_default="", nullable=False)
    fs_uniquifier = db.Column(db.String(64), nullable=True, server_default="")
    active = db.Column(db.Boolean(), default=True, server_default=sql.expression.true())
    confirmed_at = db.Column(db.DateTime(timezone=False))
    last_login_at = db.Column(db.DateTime(timezone=False))
    current_login_at = db.Column(db.DateTime(timezone=False))
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    subscribe_daily_schedule = db.Column(db.Boolean(), default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )
    # when does this subscription expire?
    expiry = db.Column(db.Date(), default=one_year_later)

    organisation_id = db.Column(db.Integer, db.ForeignKey("organisation.id"))
    organisation = db.relationship(
        "Organisation", backref="users", lazy=False, foreign_keys=[organisation_id]
    )

    # premium committee subscriptions, in addition to any that the user's organisation might have
    subscriptions = db.relationship(
        "Committee", secondary="user_committee", passive_deletes=True
    )

    # committees that the user chooses to follow
    following = db.relationship(
        "Committee", secondary="user_following", passive_deletes=True
    )

    # alerts for changes to committees
    committee_alerts = db.relationship(
        "Committee",
        secondary="user_committee_alerts",
        passive_deletes=True,
        lazy="joined",
    )
    roles = db.relationship(
        "Role", secondary="roles_users", backref=db.backref("users", lazy="dynamic")
    )

    def __str__(self):
        return str(self.email)

    def is_confirmed(self):
        return self.confirmed_at is not None

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
        if self.has_role("editor"):
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
        return self.organisation and self.organisation.subscribed_to_committee(
            committee
        )

    def gets_alerts_for(self, committee):
        from ..models.resources import Committee

        if not isinstance(committee, Committee):
            committee = Committee.query.get(committee)
        return committee in self.committee_alerts

    def follows(self, committee):
        from ..models.resources import Committee

        if not isinstance(committee, Committee):
            committee = Committee.query.get(committee)
        return committee in self.following

    def get_followed_committee_meetings(self):
        from ..models.resources import CommitteeMeeting

        following = CommitteeMeeting.committee_id.in_([f.id for f in self.following])
        return CommitteeMeeting.query.filter(following).order_by(
            desc(CommitteeMeeting.date)
        )

    def follow_committee(self, committee):
        from ..models.resources import Committee

        if not isinstance(committee, Committee):
            committee = Committee.query.get(committee)
        self.following.append(committee)

    def unfollow_committee(self, committee):
        from ..models.resources import Committee

        if not isinstance(committee, Committee):
            committee = Committee.query.get(committee)
        self.following.remove(committee)

    @validates("organisation")
    def validate_organisation(self, key, org):
        if org:
            self.expiry = org.expiry
        return org

    @validates("email")
    def validate_email(self, key, email):
        if email:
            email = email.lower()
        if not self.organisation and email:
            user_domain = email.split("@")[-1]
            self.organisation = Organisation.query.filter_by(domain=user_domain).first()
        return email

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp.pop("password")
        tmp.pop("last_login_ip")
        tmp.pop("current_login_ip")
        tmp.pop("last_login_at")
        tmp.pop("current_login_at")
        tmp.pop("confirmed_at")
        tmp.pop("login_count")
        tmp["has_expired"] = self.has_expired()

        # send committee alerts back as a dict
        alerts_dict = {}
        if tmp.get("committee_alerts"):
            for committee in tmp["committee_alerts"]:
                alerts_dict[committee["id"]] = committee.get("name")
        tmp["committee_alerts"] = alerts_dict
        return tmp


def user_confirmed_handler(sender, user, **kwargs):

    html = render_template("post_confirm_welcome_email.html")
    msg = Message(
        subject="Welcome to the Parliamentary Monitoring Group",
        recipients=[user.email],
        html=html,
    )
    app.extensions.get("mail").send(msg)


roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
)

organisation_committee = db.Table(
    "organisation_committee",
    db.Column(
        "organisation_id",
        db.Integer(),
        db.ForeignKey("organisation.id", ondelete="CASCADE"),
    ),
    db.Column(
        "committee_id", db.Integer(), db.ForeignKey("committee.id", ondelete="CASCADE")
    ),
    db.UniqueConstraint("organisation_id", "committee_id"),
)


user_committee = db.Table(
    "user_committee",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE")),
    db.Column(
        "committee_id", db.Integer(), db.ForeignKey("committee.id", ondelete="CASCADE")
    ),
)

user_following = db.Table(
    "user_following",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE")),
    db.Column(
        "committee_id", db.Integer(), db.ForeignKey("committee.id", ondelete="CASCADE")
    ),
    db.Column(
        "created_at",
        db.DateTime(timezone=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=func.now(),
    ),
)

user_committee_alerts = db.Table(
    "user_committee_alerts",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE")),
    db.Column(
        "committee_id", db.Integer(), db.ForeignKey("committee.id", ondelete="CASCADE")
    ),
)


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(
    app,
    user_datastore,
    confirm_register_form=forms.RegisterForm,
    send_confirmation_form=forms.SendConfirmationForm,
)
user_confirmed.connect(user_confirmed_handler, app)
