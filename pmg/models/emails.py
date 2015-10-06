import re
import logging
import datetime

from sqlalchemy import func

from pmg import db


log = logging.getLogger(__name__)


class EmailTemplate(db.Model):
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1024))
    subject = db.Column(db.String(100))
    body = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())

    @property
    def utm_campaign(self):
        return re.sub(r'[^a-z0-9 -]+', '', self.name.lower()).replace(' ', '-')


class SavedSearch(db.Model):
    """ A search saved by a user that they get email
    alerts about.
    """
    __tablename__ = 'search_alert'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref='saved_searchs', lazy=True)
    # search terms
    search = db.Column(db.String(255), nullable=False)
    # only search for some items?
    content_type = db.Column(db.String(255))
    # only search linked to a committee?
    committee_id = db.Column(db.Integer, db.ForeignKey('committee.id', ondelete='CASCADE'))
    committee = db.relationship('Committee', lazy=True)

    # The last time an alert was sent. We compare new search results to this to determine
    # if they're fresh
    last_alerted_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    created_at = db.Column(db.DateTime(timezone=True), index=True, unique=False, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.current_timestamp())

    def check_and_send_alert(self):
        """ Check if there are new items for this search and send an
        alert if there are.
        """
        hits = self.find_new_hits()
        if hits:
            log.info("Found %d new results for saved search %s" % (len(hits), self))
            self.send_alert(hits)

    def send_alert(self, hits):
        """ Send an email alert for the search results in +hits+.
        """
        self.last_alerted_at = datetime.datetime.utcnow()
        # TODO: send email

    def find_new_hits(self):
        from pmg.search import Search

        # TODO: could also pass last_updated_at in as a filter
        search = Search().search(self.search, document_type=self.content_type, committee=self.committee_id)
        if 'hits' not in search:
            log.warn("Error doing search for %s: %s" % (self, search))
            return

        # TODO: do we index the updated_at field?
        # find the most recent results
        return [r for r in search['hits']['hits'] if r['_source']['date'] > self.last_alerted_at]

    def __repr__(self):
        return u'<SavedSearch id=%s user=%s>' % (self.id, self.user)

    @classmethod
    def send_all_alerts(cls):
        """ Find saved searches with new content and send the email alerts.
        """
        for alert in SavedSearch.query.all():
            alert.check_and_send_alert()

    @classmethod
    def find(cls, user, q, content_type=None, committee_id=None):
        return cls.query.filter(
            cls.user == user,
            cls.search == q,
            cls.content_type == content_type,
            cls.committee_id == committee_id).first()

    @classmethod
    def find_or_create(cls, user, q, content_type=None, committee_id=None):
        search = cls.find(user, q, content_type, committee_id)
        if not search:
            search = cls(user=user, search=q, content_type=content_type, committee_id=committee_id)
            search.last_alerted_at = datetime.datetime.utcnow()
            db.session.add(search)
        return search
