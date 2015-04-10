from itertools import chain
import logging

from flask import redirect, request, url_for, jsonify, flash
from flask.ext.admin import BaseView, expose
from flask_mail import Message
from flask_wtf import Form
from wtforms import StringField, TextAreaField, validators, HiddenField, BooleanField, SelectMultipleField
from wtforms.widgets import CheckboxInput
from wtforms.fields.html5 import EmailField
from sqlalchemy.orm import lazyload
from sqlalchemy.sql.expression import distinct
from sqlalchemy.sql.functions import count
import mandrill

from pmg.models import EmailTemplate, User, Committee, user_committee_alerts, CommitteeMeeting
from pmg import app, db, mail
from rbac import RBACMixin

log = logging.getLogger(__name__)

class EmailAlertView(RBACMixin, BaseView):
    required_roles = ['editor']

    @expose('/')
    def index(self):
        templates = db.session.query(EmailTemplate).order_by(EmailTemplate.name).all()
        return self.render('admin/alerts/index.html',
                templates=templates)

    @expose('/new', methods=['GET', 'POST'])
    def new(self):
        template = None
        if request.values.get('template_id'):
            template = db.session.query(EmailTemplate).get(request.values.get('template_id'))

        if not template:
            return redirect(url_for('alerts.index'))

        form = EmailAlertForm(obj=template)
        form.template_id.data = form.template_id.data or template.id

        # pull in some values from the querystring
        for field in ('committee_meeting_id',):
            if field in request.args:
                getattr(form, field).data = request.args[field]
        if 'committee_ids' in request.args:
            form.committee_ids.data = [int(i) for i in request.args.getlist('committee_ids')]

        if 'prefill' in request.args:
            form.process_substitutions()

        if form.validate_on_submit() and form.previewed.data == '1':
            # send it
            form.generate_email()
            if not form.recipients:
                flash('There are no recipients to send this email to.', 'error')
            else:
                form.send_email()
                flash("Your email alert with subject '%s' has been sent to %d recipients." % (form.message.subject, len(form.recipients)))
                return redirect(url_for('alerts.index'))

        # force a preview before being sent again
        form.previewed.data = '0'

        return self.render('admin/alerts/new.html',
                form=form)

    @expose('/preview', methods=['POST'])
    def preview(self):
        form = EmailAlertForm()
        if form.validate_on_submit():
            form.generate_email()
            return self.render('admin/alerts/preview.html', form=form)

        else:
            return ('validation failed', 400)


    @expose('/sent', methods=['GET'])
    def sent(self):
        return self.render('admin/alerts/sent.html', form=form)


class EmailAlertForm(Form):
    template_id = HiddenField('template_id', [validators.Required()])
    previewed = HiddenField('previewed', default='0')
    subject = StringField('Subject', [validators.Required()])
    # This MUST be an email address, the Mandrill API doesn't allow us to do names and emails in one field
    from_email = EmailField('From address', [validators.Required()], default='alerts@pmg.org.za')
    body = TextAreaField('Content of the alert')

    # recipient options
    daily_schedule_subscribers = BooleanField('Daily schedule subscribers')
    committee_ids = SelectMultipleField('Committee Subscribers', [validators.Optional()], coerce=int, widget=CheckboxInput)

    # linked models
    committee_meeting_id = HiddenField('committee_meeting_id')

    def __init__(self, *args, **kwargs):
        super(EmailAlertForm, self).__init__(*args, **kwargs)
        committee_list = Committee.query.order_by(Committee.house_id.desc()).order_by(Committee.name).all()

        # count of daily schedule subscribers
        subs = User.query.filter(User.subscribe_daily_schedule == True).count()
        self.daily_schedule_subscribers.label.text += " (%d)" % subs

        # count subscribers for committees
        subscriber_counts = {t[0]: t[1]
                for t in db.session\
                    .query(user_committee_alerts.c.committee_id,
                           count(1))\
                    .group_by(user_committee_alerts.c.committee_id)\
                    .all()}

        self.committee_ids.choices = [(c.id, "%s - %s (%d)" % (c.house.name, c.name, subscriber_counts.get(c.id, 0))) for c in committee_list]

        self.message = None
        self.ad_hoc_mapper = []
        for committee in committee_list:
            if committee.ad_hoc:
                self.ad_hoc_mapper.append(committee.id)

    @property
    def template(self):
        if not hasattr(self, '_template'):
            self._template = EmailTemplate.query.get(self.template_id.data)
        return self._template

    @property
    def committee_meeting(self):
        if self.committee_meeting_id.data:
            return CommitteeMeeting.query.get(self.committee_meeting_id.data)

    def process_substitutions(self):
        committee_meeting = self.committee_meeting
        committee_meeting.date = committee_meeting.date.strftime('%Y-%m-%d')

        for field in (self.subject, self.body):
            try:
                field.data = field.data.format(committee_meeting=self.committee_meeting)
            except KeyError as e:
                if not field.errors:
                    field.errors = []
                field.errors.append("Couldn't substitute field %s" % e)

    def send_email(self):
        # TODO: don't send in development?

        if not self.message:
            self.generate_email()

        recipients = [{'email': r.email} for r in self.recipients]
        merge_vars = [{"rcpt": r.email, "vars": [{"name": "NAME", "content": r.name or 'Subscriber'}]} for r in self.recipients]

        msg = {
            "html": self.message.html,
            "subject": self.message.subject,
            "from_name": "PMG Notifications",
            "from_email": self.message.sender,
            "to": recipients,
            "merge_vars": merge_vars,
            "track_opens": True,
            "track_clicks": True,
            "preserve_recipients": False,
            "google_analytics_campaign": self.template.utm_campaign,
            "subaccount": app.config['MANDRILL_ALERTS_SUBACCOUNT'],
        }

        log.info("Email will be sent to %d recipients." % len(recipients))
        log.info("Sending email via mandrill: %s" % msg)

        mandrill_client = mandrill.Mandrill(app.config['MANDRILL_API_KEY'])
        mandrill_client.messages.send(message=msg)

    def generate_email(self):
        # TODO: render

        self.recipients = self.get_recipient_users()

        self.message = Message(
                subject=self.subject.data,
                sender=self.from_email.data,
                html=self.body.data)

    def get_recipient_users(self):
        groups = []

        if self.daily_schedule_subscribers.data:
            log.info("Email recipients includes daily schedule subscribers")
            groups.append(User.query
                    .options(
                        lazyload(User.organisation),
                        lazyload(User.committee_alerts),
                    )\
                    .filter(User.subscribe_daily_schedule == True)
                    .all())

        if self.committee_ids.data:
            log.info("Email recipients includes subscribers for these committees: %s" % self.committee_ids.data)
            user_ids = db.session\
                    .query(distinct(user_committee_alerts.c.user_id))\
                    .filter(user_committee_alerts.c.committee_id.in_(self.committee_ids.data))\
                    .all()
            user_ids = [u[0] for u in user_ids]

            groups.append(User.query
                    .options(
                        lazyload(User.organisation),
                        lazyload(User.committee_alerts),
                    )\
                    .filter(User.id.in_(user_ids))
                    .all())

        return set(u for u in chain(*groups))
