import re
import datetime
import logging
import os

from sqlalchemy import desc, Index, func, sql
from sqlalchemy.orm import backref, validates, joinedload
from sqlalchemy.event import listen
from sqlalchemy import UniqueConstraint

from flask import url_for
from flask.ext.sqlalchemy import models_committed
from flask_security import current_user

from werkzeug import secure_filename

from pmg import app, db
from pmg.search import Search

import serializers
from .s3_upload import S3Bucket
from .base import ApiResource, resource_slugs, FileLinkMixin

STATIC_HOST = app.config['STATIC_HOST']

logger = logging.getLogger(__name__)
s3_bucket = S3Bucket()


def allowed_file(filename):
    tmp = '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    logger.debug("File upload for '%s' allowed? %s" % (filename, tmp))
    return tmp

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


class Bill(ApiResource, db.Model):
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
    versions = db.relationship("BillVersion", backref='bill', cascade='all, delete, delete-orphan')

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

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.year))


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
    file_path = db.Column(db.String(255), nullable=False)
    file_bytes = db.Column(db.BigInteger())
    origname = db.Column(db.String(255))
    description = db.Column(db.String(255))
    playtime = db.Column(db.String(10))

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp['url'] = self.url
        return tmp

    @property
    def url(self):
        """ The friendly URL a user can use to download this file. """
        return url_for('docs', path=self.file_path)

    def from_upload(self, file_data):
        """ Handle a POST-based file upload and use it as the content for this file. """
        if not allowed_file(file_data.filename):
            raise Exception("File type not allowed.")

        # save file to disk
        filename = secure_filename(file_data.filename)
        path = os.path.join(app.config['UPLOAD_PATH'], filename)

        logger.debug('saving uploaded file %s to %s' % (filename, path))
        file_data.save(path)

        # save attributes
        self.file_mime = file_data.mimetype
        self.file_bytes = os.stat(path).st_size

        # upload saved file to S3
        self.file_path = s3_bucket.upload_file(path, filename)

    def delete_from_s3(self):
        logger.info("Deleting %s from S3" % self.file_path)
        key = s3_bucket.bucket.get_key(self.file_path)
        key.delete()

    def __unicode__(self):
        if self.title:
            return u'%s (%s)' % (self.title, self.file_path)
        return u'%s' % self.file_path

@models_committed.connect_via(app)
def delete_file_from_s3(sender, changes):
    for obj, change in changes:
        # obj is the changed object, change is one of: update, insert, delete
        if change == 'delete' and isinstance(obj, File):
            try:
                obj.delete_from_s3()
            except Exception as e:
                logger.warn("Couldn't delete %s from S3, ignoring: %s" % (obj, e.message), exc_info=e)


class Event(ApiResource, db.Model):
    """ An event is a generic model which represents an event that took
    place in Parliament at a certain time and may have rich content associated
    with it.
    """

    __tablename__ = "event"
    __mapper_args__ = {
        'polymorphic_on': 'type'
    }

    id = db.Column(db.Integer, index=True, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), nullable=False)
    title = db.Column(db.String(1024), nullable=False)
    type = db.Column(db.String(50), index=True, nullable=False)

    # this is the legacy node id from the old drupal database and is used
    # in conjunction with the Redirect class to work out redirects
    # from legacy URLs to new URLs
    nid = db.Column(db.Integer())

    # optional content
    body = db.Column(db.Text())
    summary = db.Column(db.Text())

    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), index=True)
    member = db.relationship('Member', backref='events')
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete='SET NULL'), index=True)
    committee = db.relationship('Committee', lazy=False, backref=backref( 'events', order_by=desc('Event.date')))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), index=True)
    house = db.relationship('House', lazy=False, backref=backref('events', order_by=desc('Event.date')))
    bills = db.relationship('Bill', secondary='event_bills', backref=backref('events'), cascade="save-update, merge")
    chairperson = db.Column(db.String(256))

    # did this meeting involve public participation?
    public_participation = db.Column(db.Boolean, default=False, server_default=sql.expression.false())
    # feature this on the front page?
    featured = db.Column(db.Boolean(), default=False, server_default=sql.expression.false(), nullable=False, index=True)
    # optional file attachments
    files = db.relationship('EventFile', lazy=True, cascade="all, delete, delete-orphan")

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
    db.Column('event_id', db.Integer(), db.ForeignKey('event.id', ondelete="CASCADE")),
    db.Column('bill_id', db.Integer(), db.ForeignKey('bill.id', ondelete="CASCADE")))


class EventFile(FileLinkMixin, db.Model):
    __tablename__ = "event_files"

    id = db.Column(db.Integer, index=True, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete="CASCADE"), index=True, nullable=False)
    event = db.relationship('Event')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


class CommitteeMeeting(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'committee-meeting'
    }

    def check_permission(self):
        # by default, all committee meetings are accessible
        if self.committee and self.committee.premium:
            if not current_user.is_authenticated():
                return False
            return current_user.subscribed_to_committee(self.committee)
        return True

    @property
    def alert_template(self):
        from pmg.models.emails import EmailTemplate
        return EmailTemplate.query.filter(EmailTemplate.name == "Minute alert").first()

    def to_dict(self, include_related=False):
        tmp = super(CommitteeMeeting, self).to_dict(include_related=include_related)
        # check user permissions, popping some content if required
        if not self.check_permission():
            # remove premium content
            tmp['premium_content_excluded'] = True
            del tmp['body']
            del tmp['summary']
            if 'files' in tmp:
                del tmp['files']

        return tmp

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.date))


class Hansard(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'plenary'
    }

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.date))


class Briefing(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'media-briefing'
    }

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.date))


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


class BillCommenced(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-act-commenced'
    }


class BillUpdate(Event):
    __mapper_args__ = {
        'polymorphic_identity': 'bill-updated'
    }


class MembershipType(ApiResource, db.Model):

    __tablename__ = "membership_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self, include_related=False):
        # reduce this model to a string
        return self.name

    def __unicode__(self):
        return unicode(self.name)


class Member(ApiResource, db.Model):

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

    memberships = db.relationship('Membership', backref=backref("member", lazy="joined"), lazy='joined', cascade="all, delete, delete-orphan")

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

    @classmethod
    def list(cls):
        return cls.query\
            .options(joinedload('house'),
                     joinedload('province'),
                     joinedload('memberships.committee'))\
            .filter(Member.current == True)\
            .order_by(Member.name)


class Committee(ApiResource, db.Model):

    __tablename__ = "committee"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    about = db.Column(db.Text())
    contact_details = db.Column(db.Text())
    ad_hoc = db.Column(db.Boolean(), default=False, server_default=sql.expression.false(), nullable=False)
    premium = db.Column(db.Boolean(), default=False, server_default=sql.expression.false(), nullable=False)

    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    house = db.relationship('House', lazy='joined')

    memberships = db.relationship('Membership', backref="committee", cascade='all, delete, delete-orphan', passive_deletes=True)

    @classmethod
    def premium_for_select(cls):
        return cls.query.filter(cls.premium == True)\
                .order_by(cls.name)\
                .all()

    @classmethod
    def for_related(cls, other):
        """ Those Committees that are linked to `other` via a foreign key.
        """
        ids = set(x[0] for x in db.session.query(func.distinct(other.committee_id)).all())
        return cls.query.filter(cls.id.in_(ids)).order_by(cls.name)

    @classmethod
    def list(cls):
        return cls.query.order_by(cls.house_id, cls.name)

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
    member_id = db.Column(db.Integer, db.ForeignKey('member.id', ondelete="CASCADE"), nullable=False)

    def __unicode__(self):
        tmp = u" - ".join([unicode(self.type),
                           unicode(self.member),
                           unicode(self.committee)])
        return unicode(tmp)


# === Schedule === #

class Schedule(ApiResource, db.Model):

    __tablename__ = "schedule"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    meeting_date = db.Column(db.Date())
    meeting_time = db.Column(db.Text())
    houses = db.relationship("House", secondary='schedule_house_join')

    @classmethod
    def list(cls):
        current_time = datetime.datetime.utcnow()
        return cls.query\
                .order_by(desc(cls.meeting_date))\
                .filter(Schedule.meeting_date >= current_time)

schedule_house_table = db.Table(
    'schedule_house_join', db.Model.metadata,
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id')),
    db.Column('house_id', db.Integer, db.ForeignKey('house.id'))
)


# === Questions Replies === #

class QuestionReply(ApiResource, db.Model):

    __tablename__ = "question_reply"

    # override the default of question-reply for legacy reasons
    slug_prefix = "question_reply"

    id = db.Column(db.Integer, primary_key=True)
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship('Committee', backref=db.backref('questions_replies'), lazy='joined')
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    body = db.Column(db.Text)
    question_number = db.Column(db.String(255))
    nid = db.Column(db.Integer())

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


# === Tabled Committee Report === #

class TabledCommitteeReport(ApiResource, db.Model):

    __tablename__ = "tabled_committee_report"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    body = db.Column(db.Text())
    summary = db.Column(db.Text())
    nid = db.Column(db.Integer())

    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship('Committee', backref=db.backref('tabled_committee_reports'))
    files = db.relationship("TabledCommitteeReportFile", lazy='joined', cascade="all, delete, delete-orphan")

    def __unicode__(self):
        return self.title or ('<TabledCommitteeReport %s>' % self.id)

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


class TabledCommitteeReportFile(FileLinkMixin, db.Model):
    __tablename__ = 'tabled_committee_report_file_join'

    id = db.Column(db.Integer, primary_key=True)
    tabled_committee_report_id = db.Column(db.Integer, db.ForeignKey('tabled_committee_report.id', ondelete='CASCADE'), index=True, nullable=False)
    tabled_committee_report = db.relationship('TabledCommitteeReport')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


# === Calls for comment === #

class CallForComment(ApiResource, db.Model):

    __tablename__ = "call_for_comment"

    id = db.Column(db.Integer, primary_key=True)
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship('Committee', backref=db.backref('calls_for_comments'), lazy='joined')
    title = db.Column(db.Text(), nullable=False)
    start_date = db.Column(db.Date(), nullable=False)
    end_date = db.Column(db.Date())
    body = db.Column(db.Text())
    summary = db.Column(db.Text())
    nid = db.Column(db.Integer())

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


# === Policy document === #

class PolicyDocument(ApiResource, db.Model):

    __tablename__ = "policy_document"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    effective_date = db.Column(db.Date())
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())

    files = db.relationship("PolicyDocumentFile", lazy='joined', cascade="all, delete, delete-orphan")

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


class PolicyDocumentFile(FileLinkMixin, db.Model):
    __tablename__ = 'policy_document_file_join'

    id = db.Column(db.Integer, primary_key=True)
    policy_document_id = db.Column(db.Integer, db.ForeignKey('policy_document.id', ondelete='CASCADE'), index=True, nullable=False)
    policy_document = db.relationship('PolicyDocument')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


# === Gazette === #

class Gazette(ApiResource, db.Model):

    __tablename__ = "gazette"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    effective_date = db.Column(db.Date())
    start_date = db.Column(db.Date())
    nid = db.Column('nid', db.Integer())

    files = db.relationship("GazetteFile", lazy='joined', cascade="all, delete, delete-orphan")

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


class GazetteFile(FileLinkMixin, db.Model):
    __tablename__ = "gazette_file_join"

    id = db.Column(db.Integer, primary_key=True)
    gazette_id = db.Column(db.Integer, db.ForeignKey('gazette.id', ondelete='CASCADE'), index=True, nullable=False)
    gazette = db.relationship('Gazette')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


# === Featured Content === #

class Featured(db.Model):

    __tablename__ = "featured"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    blurb = db.Column(db.Text())
    link = db.Column(db.String(255))
    start_date = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)

# === Daily schedules === #


class DailySchedule(ApiResource, db.Model):

    __tablename__ = "daily_schedule"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    start_date = db.Column(db.Date())
    schedule_date = db.Column(db.Date())
    body = db.Column(db.Text())
    nid = db.Column(db.Integer())

    files = db.relationship("DailyScheduleFile", lazy='joined', cascade="all, delete, delete-orphan")

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


class DailyScheduleFile(FileLinkMixin, db.Model):
    __tablename__ = "daily_schedule_file_join"

    id = db.Column(db.Integer, primary_key=True)
    daily_schedule_id = db.Column(db.Integer, db.ForeignKey('daily_schedule.id', ondelete='CASCADE'), index=True, nullable=False)
    daily_schedule = db.relationship('DailySchedule')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


# Listen for model updates
@models_committed.connect_via(app)
def on_models_changed(sender, changes):
    searcher = Search()

    for obj, change in changes:
        # obj is the changed object, change is one of: update, insert, delete

        if searcher.indexable(obj):
            logger.info('Reindexing changed item: %s %s' % (change, obj))

            if change == 'delete':
                # deleted
                searcher.delete_obj(obj)
            else:
                # updated or inserted
                searcher.add_obj(obj)


# Register all the resource types. This ensures they show up in the API and are searchable
ApiResource.register(Bill)
ApiResource.register(Briefing)
ApiResource.register(CallForComment)
ApiResource.register(Committee)
ApiResource.register(CommitteeMeeting)
ApiResource.register(DailySchedule)
ApiResource.register(Gazette)
ApiResource.register(Hansard)
ApiResource.register(Member)
ApiResource.register(PolicyDocument)
ApiResource.register(QuestionReply)
ApiResource.register(Schedule)
ApiResource.register(TabledCommitteeReport)
