from flask_wtf import Form as BaseForm
from wtforms import TextField, validators
from flask.ext.wtf.recaptcha import RecaptchaField
from flask_security.forms import ConfirmRegisterForm as BaseRegisterForm, NextFormMixin


# Add NextFormMixin ourselves because it seems to be expected but missing as at
# Flask-Security 1.7.4
class RegisterForm(BaseRegisterForm, NextFormMixin):
    recaptcha = RecaptchaField()


class CorrectThisPageForm(BaseForm):
    email = TextField('Email', [validators.Optional()])
    details = TextField('Details', [validators.Optional()])
    url = TextField('URL', [validators.Optional()])
    recaptcha = RecaptchaField()
