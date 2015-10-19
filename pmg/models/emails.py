import re
import logging
import arrow
import pytz

from sqlalchemy import func
import mandrill
from flask import render_template, url_for

from pmg import db, app
from pmg.models.resources import DailySchedule


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
    __tablename__ = 'saved_search'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref='saved_searches', lazy=True)
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

        NOTE: this commits the database session, to prevent later errors from causing
        us to send duplicate emails.
        """
        # we embed this into the actual email template
        html = render_template('saved_search_alert.html', search=self, results=hits)

        send_mandrill_email(
            subject="New matches for your search '%s'" % self.search,
            from_name="PMG Notifications",
            from_email="alerts@pmg.org.za",
            recipient_users=[self.user],
            html=html,
            utm_campaign='searchalert',
        )

        # save that we sent this alert
        self.last_alerted_at = arrow.utcnow().datetime
        db.session.commit()

    def find_new_hits(self):
        from pmg.search import Search

        # find hits updated since the last time we did this search
        search = Search().search(self.search, document_type=self.content_type, committee=self.committee_id,
                                 exclude_document_types=[DailySchedule.resource_content_type])

        if 'hits' not in search:
            log.warn("Error doing search for %s: %s" % (self, search))
            return

        timestamp = self.last_alerted_at.astimezone(pytz.utc)
        hits = search['hits']['hits']
        hits = [h for h in hits if arrow.get(h['_source']['updated_at']).datetime >= timestamp]

        return hits

    def url(self, **kwargs):
        params = {'q': self.search}

        if self.content_type:
            params['filter[type]'] = self.content_type

        if self.committee_id:
            params['filter[committee]'] = self.committee_id

        params.update(kwargs)
        return url_for('search', **params)

    @property
    def friendly_content_type(self):
        from pmg.search import Search
        if self.content_type:
            return Search.friendly_data_types[self.content_type]

    def __repr__(self):
        return u'<SavedSearch id=%s user=%s>' % (self.id, self.user)

    @classmethod
    def send_all_alerts(cls):
        """ Find saved searches with new content and send the email alerts.
        """
        log.info("Sending all alerts")
        for alert in SavedSearch.query.all():
            alert.check_and_send_alert()
        log.info("Sending alerts finished")

    @classmethod
    def find(cls, user, q, content_type=None, committee_id=None):
        return cls.query.filter(
            cls.user == user,
            cls.search == q.lower(),
            cls.content_type == content_type,
            cls.committee_id == committee_id).first()

    @classmethod
    def find_or_create(cls, user, q, content_type=None, committee_id=None):
        search = cls.find(user, q, content_type, committee_id)
        if not search:
            search = cls(user=user, search=q.lower(), content_type=content_type, committee_id=committee_id)
            search.last_alerted_at = arrow.utcnow().datetime
            db.session.add(search)
        return search


def send_mandrill_email(subject, from_name, from_email, recipient_users, html, utm_campaign, subaccount=None):
    """ Send an email using Mandrill, relying on Mandrill's templating system.

    :param subject: email subject
    :param from_name: name of the sender
    :param from_email: email of the sender
    :param recipient_users: array of `User` objects of recipients
    :param html: HTML body of the email
    :param utm_campaign: Google Analytics campaign (optional)
    :param subaccount: Mandrill subaccount to use (optional)
    """
    subaccount = subaccount or app.config['MANDRILL_ALERTS_SUBACCOUNT']

    recipients = [{'email': r.email} for r in recipient_users]
    merge_vars = [{"rcpt": r.email, "vars": [{"name": "NAME", "content": r.name or 'Subscriber'}]} for r in recipient_users]

    # NBNBNBNB: the email template MUST have a special DIV in it to place the content in.
    # This gets removed when importing the template into Mandrill from Mailchimp
    #  <div mc:edit="main"></div>

    template_vars = [
        {"name": "main", "content": html},
    ]

    msg = {
        "subject": subject,
        "from_name": from_name,
        "from_email": from_email,
        "to": recipients,
        "merge_vars": merge_vars,
        "track_opens": True,
        "track_clicks": True,
        "preserve_recipients": False,
        "google_analytics_campaign": utm_campaign,
        "google_analytics_domains": ["pmg.org.za"],
        "subaccount": subaccount,
    }

    log.info("Email will be sent to %d recipients." % len(recipients))
    log.info("Sending email via mandrill: %s" % msg)

    mandrill_client = mandrill.Mandrill(app.config['MANDRILL_API_KEY'])
    mandrill_client.messages.send_template(app.config["MANDRILL_ALERTS_TEMPLATE"], template_vars, msg)
