from flask import redirect, request, url_for, jsonify, flash
from flask.ext.admin import BaseView, expose
from flask_mail import Message
from flask_wtf import Form
from wtforms import StringField, TextAreaField, validators, HiddenField
from wtforms.fields.html5 import EmailField

from models import EmailTemplate
from app import app, db, mail

class EmailAlertView(BaseView):
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

    @property
    def template(self):
        if not hasattr(self, '_template'):
            self._template = EmailTemplate.query.get(self.template_id.data)
        return self._template

    def send_email(self):
        self.generate_email()
        mail.send(self.message)

    def generate_email(self):
        # TODO: render
        # TODO: recipients
        self.message = Message(
                subject=self.subject.data,
                sender=self.from_line.data,
                html=self.body.data)
