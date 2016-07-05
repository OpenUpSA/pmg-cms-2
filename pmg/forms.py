from flask_wtf import Form as BaseForm
from wtforms import TextField, validators
from flask.ext.wtf.recaptcha import RecaptchaField
from flask_security.forms import RegisterForm as BaseRegisterForm


class RegisterForm(BaseRegisterForm):
    recaptcha = RecaptchaField()


class CorrectThisPageForm(BaseForm):
    email = TextField('Email', [validators.Optional()])
    details = TextField('Details', [validators.Optional()])
    url = TextField('URL', [validators.Optional()])
    recaptcha = RecaptchaField()
