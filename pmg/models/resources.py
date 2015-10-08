import datetime
import logging
import os
import re

from sqlalchemy import desc, func, sql
from sqlalchemy.orm import backref, joinedload, validates

from flask import url_for
from flask.ext.sqlalchemy import models_committed
from flask_security import current_user

from werkzeug import secure_filename
from za_parliament_scrapers.questions import QuestionAnswerScraper

from pmg import app, db
from pmg.utils import levenshtein

import serializers
from .s3_upload import S3Bucket
from .base import ApiResource, FileLinkMixin

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

    @classmethod
    def ncop(cls):
        return cls.query.filter(cls.name_short == 'NCOP').one()

    @classmethod
    def na(cls):
        return cls.query.filter(cls.name_short == 'NA').one()


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
    __table_args__ = (db.UniqueConstraint('number', 'year', 'type_id', name='bill_number_year_type_id_key'), {})

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
    type_id = db.Column(db.Integer, db.ForeignKey('bill_type.id'), nullable=False)
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
        if app.debug:
            self.file_path = path
        else:
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
    committee = db.relationship('Committee', lazy=False, backref=backref('events', order_by=desc('Event.date')))
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
    actual_start_time = db.Column(db.Time(timezone=True))
    actual_end_time = db.Column(db.Time(timezone=True))
    pmg_monitor = db.Column(db.String(255))

    attendance = db.relationship('CommitteeMeetingAttendance', backref='meeting', cascade="all, delete, delete-orphan")

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
        tmp['attendance_url'] = url_for('api.committee_meeting_attendance', committee_meeting_id=self.id, _external=True)
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


class MembershipType(db.Model):

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

        tmp['questions_url'] = url_for('api.member_questions', member_id=self.id, _external=True)
        tmp['attendance_url'] = url_for('api.member_attendance', member_id=self.id, _external=True)

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
            .order_by(Member.name)  # noqa

    @classmethod
    def find_by_inexact_name(cls, first_name, last_name, title, threshold=0.8, members=None):
        # in the db, the name format is "last_name, title initial"
        seeking = "%s, %s %s" % (last_name, title, first_name[0])

        members = members or Member.query.all()
        best = None

        for member in members:
            score = levenshtein(member.name, seeking)
            if score >= threshold:
                if not best or score > best[1]:
                    best = (member, score)

        return best[0] if best else None


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
    minister_id = db.Column(db.Integer, db.ForeignKey('minister.id', ondelete='SET NULL'), nullable=True)
    minister = db.relationship('Minister', lazy=True)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp['questions_url'] = url_for('api.committee_questions', committee_id=self.id, _external=True)
        return tmp

    @classmethod
    def premium_for_select(cls):
        return cls.query\
                .filter(cls.premium == True)\
                .order_by(cls.name)\
                .all()  # noqa

    @classmethod
    def for_related(cls, other):
        """ Those Committees that are linked to `other` via a foreign key.
        """
        ids = set(x[0] for x in db.session.query(func.distinct(other.committee_id)).all())
        return cls.query.filter(cls.id.in_(ids)).order_by(cls.name)

    @classmethod
    def list(cls):
        return cls.query.order_by(cls.house_id, cls.name)

    @classmethod
    def find_by_inexact_name(cls, name, threshold=0.8, candidates=None):
        candidates = candidates or cls.query.all()
        best = None

        for cte in candidates:
            score = levenshtein(cte.name, name)
            if score >= threshold:
                if not best or score > best[1]:
                    best = (cte, score)

        return best[0] if best else None

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


# === Committee Questions === #
#
# Questions asked by an MP of a Committe chairperson

class CommitteeQuestion(ApiResource, db.Model):
    __tablename__ = "committee_question"

    # we mix QuestionReplies and CommitteeQuestions together
    # in ElasticSearch
    resource_content_type = "minister_question"

    # otherwise this is  based on resource_content_type
    slug_prefix = "committee-question"

    id = db.Column(db.Integer, primary_key=True)

    # TODO: delete this reference and use the minister relation instead
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship('Committee', backref=db.backref('questions'), lazy='joined')

    minister_id = db.Column(db.Integer, db.ForeignKey('minister.id', ondelete="SET NULL"))
    minister = db.relationship('Minister', lazy='joined')

    # XXX: don't forget session, numbers are unique by session only

    # Questions are also referred to by an identifier code of the form
    # [NC][OW]\d+[AEX]
    # The meaning of the parts of this identifier is as follows:
    #  - [NC] - tells you the house the question was asked in. See 'house' below.
    #  - [OW] - tells you whether the question is for oral or written answer.
    #           Questions can sometimes be transferred between being oral or
    #           written. When this happens, they may be referred to by the new
    #           identifier with everything the same except the O/W.
    #  - \d+  - (number below) Every question to a particular house in a
    #           particular year gets given another number. This number doesn't
    #           change when the question is translated or has [OW] changed.
    #  - [AEX]- Afrikaans/English/Xhosa. The language the question is currently
    #           being displayed in. Translations of the question will have a
    #           different [AEX] in the identifier.
    #
    # Note that we also store the number, house, and answer_type separately.
    code = db.Column(db.String(50), index=True, unique=False, nullable=False)

    # From the identifier discussed above.
    question_number = db.Column(db.Integer, index=True, nullable=True)

    # This is in the identifier above.
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    house = db.relationship("House", lazy=False)

    # Questions for written answer and questions for oral answer both have
    # sequence numbers. It looks like these are probably the order the questions
    # were asked in. The sequences are unique for each house for written/oral and
    # restart on 1 each session.

    # At least one of these four numbers should be non-null, and it's possible
    # for more than one to be non-null if a question is transferred from oral to written
    # or vice-versa.
    written_number = db.Column(db.Integer, nullable=True, index=True)
    oral_number = db.Column(db.Integer, nullable=True, index=True)

    # The president and vice president get their own question number sequences for
    # oral questions.
    president_number = db.Column(db.Integer, nullable=True, index=True)
    deputy_president_number = db.Column(db.Integer, nullable=True, index=True)

    answer_type = db.Column(db.Enum('oral', 'written', name='committee_question_answer_type_enum'), nullable=False)

    # Date of the question, generally the date on which it was answered. Not to
    # be confused with the date the question was published.
    date = db.Column(db.Date(), nullable=False)

    # This should always be the year from the date above, but is worth
    # storing separately so that we can easily have uniqueness constraints
    # on it.
    year = db.Column(db.Integer, index=True, nullable=False)

    # The actual text of the question.
    question = db.Column(db.Text)

    # The actual text (HTML) of the answer.
    answer = db.Column(db.Text)

    # Text of the person the question is asked of
    question_to_name = db.Column(db.String(1024))

    # Is the question a translation of one originally asked in another language.
    # Currently we are only storing questions in English.
    translated = db.Column(db.Boolean, default=False, nullable=False)

    # oral/written number, asker and askee as as string, for example:
    # '144. Mr D B Feldman (COPE-Gauteng) to ask the Minister of Defence and Military Veterans:'
    # '152. Mr D A Worth (DA-FS) to ask the Minister of Defence and Military Veterans:'
    # '254. Mr R A Lees (DA-KZN) to ask the Minister of Rural Development and Land Reform:'
    intro = db.Column(db.Text)

    # Name of the person asking the question.
    asked_by_name = db.Column(db.String(1024))
    # The actual MP asking the question. This may be null if we weren't able to link it to an MP
    asked_by_member_id = db.Column(db.Integer, db.ForeignKey('member.id', ondelete='CASCADE'))
    asked_by_member = db.relationship('Member')

    # the source document for this question
    source_file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="SET NULL"), index=True, nullable=True)
    source_file = db.relationship('File', lazy='joined')

    files = db.relationship("CommitteeQuestionFile", lazy='joined', cascade="all, delete, delete-orphan")

    # indexes for uniqueness
    __table_args__ = (
        db.UniqueConstraint('date', 'code', name='date_code_ix'),
        db.UniqueConstraint('date', 'house_id', 'oral_number', name='date_oral_number_ix'),
        db.UniqueConstraint('date', 'house_id', 'written_number', name='date_written_number_ix'),
        db.UniqueConstraint('date', 'house_id', 'president_number', name='date_president_number_ix'),
        db.UniqueConstraint('date', 'house_id', 'deputy_president_number', name='date_deputy_president_number_ix'),
    )

    def populate_from_code(self, code):
        """ Populate this question with the details contained in +code+, such as
        RNW2680-1212114.
        """
        details = QuestionAnswerScraper().details_from_name(code)

        house = details.pop('house')
        if house == 'N':
            house = House.na()
        elif house == 'C':
            house = House.ncop()
        else:
            raise ValueError("Invalid house: %s" % house)

        # TODO: session
        self.code = details['code']
        self.house = house
        self.written_number = details.get('written_number')
        self.oral_number = details.get('oral_number')
        self.question_number = self.written_number or self.oral_number
        self.president_number = details.get('president_number')
        self.deputy_president_number = details.get('deputy_president_number')
        self.date = details.get('date')
        self.answer_type = {
            'O': 'oral',
            'W': 'written',
        }[details.get('type') or 'W']

    def parse_answer_file(self, filename):
        # process the actual document text
        text, html = QuestionAnswerScraper().extract_content_from_document(filename)

        try:
            self.parse_question_text(text)
        except ValueError as e:
            logger.warn(e.message)
            self.question = text

        self.parse_answer_html(html)

    def parse_question_text(self, text):
        questions = QuestionAnswerScraper().extract_questions_from_text(text)
        if not questions:
            raise ValueError("Couldn't find any questions in the text")
        q = questions[0]

        self.question_to_name = q['questionto']
        self.committee = self.committee_from_minister_name(self.question_to_name)

        self.asked_by_name = q['askedby']
        parts = re.split(' +', self.asked_by_name)
        title, first, last = parts[0], ''.join(parts[1:-1]), parts[-1]
        self.asked_by_member = Member.find_by_inexact_name(first, last, title)

        self.question = q['question']
        self.translated = q['translated']
        self.intro = q['intro']

    def parse_answer_html(self, html):
        self.answer = QuestionAnswerScraper().extract_answer_from_html(html)

    def committee_from_minister_name(self, minister):
        name = minister\
            .replace('Minister of ', '')\
            .replace('Minister in the ', '')
        return Committee.find_by_inexact_name(name)

    @validates('date')
    def validate_date(self, key, value):
        self.year = value.year
        return value

    @validates('committee')
    def validate_committee(self, key, cte):
        if cte:
            self.minister = cte.minister
        return cte

    @classmethod
    def import_from_uploaded_answer_file(cls, upload):
        # save the file to disk
        filename = secure_filename(upload.filename)
        path = os.path.join(app.config['UPLOAD_PATH'], filename)
        logger.debug('saving uploaded file %s to %s' % (filename, path))
        upload.save(path)
        # reset file, so subsequent save() calls work
        upload.stream.seek(0)

        question = cls.import_from_answer_file(path)
        if not question.id:
            # it's new
            question.source_file = File()
            question.source_file.from_upload(upload)

        return question

    @classmethod
    def import_from_answer_file(cls, filename):
        name = os.path.splitext(os.path.basename(filename))[0]

        question = CommitteeQuestion()
        question.populate_from_code(name)

        # does it already exist?
        existing = cls.find(question.code, question.date)
        if existing:
            return existing

        question.parse_answer_file(filename)
        return question

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.date))

    @classmethod
    def find(cls, code, date):
        return cls.query.filter(cls.code == code, cls.date == date).first()


class CommitteeQuestionFile(FileLinkMixin, db.Model):
    __tablename__ = 'committee_question_file_join'

    id = db.Column(db.Integer, primary_key=True)
    committee_question_id = db.Column(db.Integer, db.ForeignKey('committee_question.id', ondelete='CASCADE'), index=True, nullable=False)
    committee_question = db.relationship('CommitteeQuestion')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


# === Legacy Questions & Replies === #
#
# Questions are stored in batches as HTML, linked to a committee.

class QuestionReply(ApiResource, db.Model):

    __tablename__ = "question_reply"

    # we mix QuestionReplies and CommitteeQuestions together
    # in ElasticSearch
    resource_content_type = "minister_question"

    # override the default of question-reply for legacy reasons
    slug_prefix = "question_reply"

    id = db.Column(db.Integer, primary_key=True)
    # TODO: delete this reference and use the minister relation instead
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete="SET NULL"))
    committee = db.relationship('Committee', backref=db.backref('questions_replies'), lazy='joined')
    minister_id = db.Column(db.Integer, db.ForeignKey('minister.id', ondelete="SET NULL"))
    minister = db.relationship('Minister', lazy='joined')
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    body = db.Column(db.Text)
    question_number = db.Column(db.String(255))
    nid = db.Column(db.Integer())
    files = db.relationship("QuestionReplyFile", lazy='joined', cascade="all, delete, delete-orphan")

    @validates('committee')
    def validate_committee(self, key, cte):
        if cte:
            self.minister = cte.minister
        return cte

    @classmethod
    def list(cls):
        return cls.query.order_by(desc(cls.start_date))


class QuestionReplyFile(FileLinkMixin, db.Model):
    __tablename__ = 'question_reply_file_join'

    id = db.Column(db.Integer, primary_key=True)
    question_reply_id = db.Column(db.Integer, db.ForeignKey('question_reply.id', ondelete='CASCADE'), index=True, nullable=False)
    question_reply = db.relationship('QuestionReply')
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete="CASCADE"), index=True, nullable=False)
    file = db.relationship('File', lazy='joined')


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
    committee = db.relationship('Committee', backref=db.backref('tabled_committee_reports'), lazy=False)
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


class CommitteeMeetingAttendance(ApiResource, db.Model):
    __tablename__ = "committee_meeting_attendance"
    """
    Attendance abbreviations:
        A:   Absent
        AP:  Absent with Apologies
        DE:  Departed Early
        L:   Arrived Late
        LDE: Arrived Late and Departed Early
        P:   Present
        U:   Unknown
    """
    id = db.Column(db.Integer, primary_key=True)
    alternate_member = db.Column(db.Boolean(), default=False, server_default=sql.expression.false(), nullable=False)
    # TODO: Y shouldn't be an option
    attendance = db.Column(db.Enum('A', 'AP', 'DE', 'L', 'LDE', 'P', 'Y', 'U', name='meeting_attendance_enum'), nullable=False)
    chairperson = db.Column(db.Boolean(), default=False, nullable=False)
    meeting_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id', ondelete='CASCADE'), nullable=False)
    member = db.relationship('Member', lazy=False)

    @classmethod
    def list(cls):
        return cls.query.join(CommitteeMeeting).order_by(CommitteeMeeting.date.desc())


db.Index('meeting_member_ix', CommitteeMeetingAttendance.meeting_id, CommitteeMeetingAttendance.member_id, unique=True)


class Minister(ApiResource, db.Model):
    __tablename__ = "minister"
    """
    A ministerial position to which questions may be asked.
    This is the position, not the person who holds that position.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self, include_related=False):
        tmp = serializers.model_to_dict(self, include_related=include_related)
        tmp['questions_url'] = url_for('api.minister_questions', minister_id=self.id, _external=True)
        return tmp

    def __unicode__(self):
        return unicode(self.name)

    @classmethod
    def list(cls):
        return cls.query.order_by(cls.name)


# Listen for model updates
@models_committed.connect_via(app)
def on_models_changed(sender, changes):
    from pmg.search import Search
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
ApiResource.register(CommitteeQuestion)
ApiResource.register(DailySchedule)
ApiResource.register(Gazette)
ApiResource.register(Hansard)
ApiResource.register(Member)
ApiResource.register(Minister)
ApiResource.register(PolicyDocument)
ApiResource.register(QuestionReply)
ApiResource.register(Schedule)
ApiResource.register(TabledCommitteeReport)
ApiResource.register(CommitteeMeetingAttendance)
