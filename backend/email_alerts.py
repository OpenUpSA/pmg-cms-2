from itertools import chain

from flask import redirect, request, url_for, jsonify, flash
from flask.ext.admin import BaseView, expose
from flask_mail import Message
from flask_wtf import Form
from wtforms import StringField, TextAreaField, validators, HiddenField, BooleanField, SelectMultipleField
from wtforms.widgets import CheckboxInput
from wtforms.fields.html5 import EmailField

from models import EmailTemplate, User, Committee
from app import app, db, mail
from rbac import RBACMixin

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

        if form.validate_on_submit() and form.previewed.data == '1':
            # send it
            form.generate_email()
            if not form.message.recipients:
                flash('There are no recipients to send this email to.', 'error')
            else:
                form.send_email()
                flash('Your email alert has been sent.')
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
    from_line = EmailField('From', [validators.Required()], default='subscribe@pmg.org.za')
    body = TextAreaField('Content of the alert')

    # recipient options
    daily_schedule_subscribers = BooleanField('Daily schedule subscribers')
    bill_subscribers = BooleanField('Newly introduced bill subscribers')
    call_for_comment_subscribers = BooleanField('Calls for comment subscribers')

    committee_ids = SelectMultipleField('Committee Subscribers', [validators.Optional()], coerce=int, widget=CheckboxInput)

    def __init__(self, *args, **kwargs):
        super(EmailAlertForm, self).__init__(*args, **kwargs)

        self.committee_ids.choices = [(c.id, c.name) for c in Committee.query.order_by(Committee.name).all()]


    @property
    def template(self):
        if not hasattr(self, '_template'):
            self._template = EmailTemplate.query.get(self.template_id.data)
        return self._template

    def send_email(self):
        mail.send(self.message)

    def generate_email(self):
        # TODO: render
        recipients = self.get_recipients()

        self.message = Message(
                subject=self.subject.data,
                sender=self.from_line.data,
                html=self.body.data,
                recipients=recipients)

    def get_recipients(self):
        groups = []

        if self.daily_schedule_subscribers.data:
            groups.append(User.query.filter(User.subscribe_daily_schedule == True).all())

        if self.bill_subscribers.data:
            groups.append(User.query.filter(User.subscribe_bill == True).all())

        if self.call_for_comment_subscribers.data:
            groups.append(User.query.filter(User.subscribe_call_for_comment == True).all())

        if self.committee_ids.data:
            groups.append(User.query
                    .join(User.subscriptions)
                    .filter(Committee.id.in_(self.committee_ids.data))
                    .all())

        return set(u.email for u in chain(*groups) if u)
