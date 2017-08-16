from flask_wtf import Form as BaseForm
from wtforms import TextField, validators
from flask.ext.wtf.recaptcha import RecaptchaField
from flask_security.forms import (
    ConfirmRegisterForm as BaseRegisterForm,
    SendConfirmationForm as BaseSendConfirmationForm,
    NextFormMixin,
)


# Add NextFormMixin ourselves because it seems to be expected but missing as at
# Flask-Security 1.7.4
class RegisterForm(BaseRegisterForm, NextFormMixin):
    recaptcha = RecaptchaField()


# Add NextFormMixin ourselves because it seems to be expected but missing as at
# Flask-Security 1.7.4
class SendConfirmationForm(BaseSendConfirmationForm, NextFormMixin):
    pass


class CorrectThisPageForm(BaseForm):
    email = TextField('Email', [validators.Optional()])
    details = TextField('Details', [validators.Optional()])
    url = TextField('URL', [validators.Optional()])
    recaptcha = RecaptchaField()
