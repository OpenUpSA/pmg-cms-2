from flask import request, current_app, flash, url_for
from flask_wtf import Form as BaseForm
from wtforms import TextField, PasswordField, validators, \
    SubmitField, HiddenField, BooleanField, ValidationError, Field, \
    SelectField
from wtforms.fields.html5 import EmailField


_default_field_labels = {
    'email': 'Email Address',
    'password': 'Password',
    'remember_me': 'Remember Me',
    'login': 'Login',
    'retype_password': 'Retype Password',
    'register': 'Sign up',
    'send_confirmation': 'Resend Confirmation Instructions',
    'recover_password': 'Recover Password',
    'reset_password': 'Reset Password',
    'retype_password': 'Retype Password',
    'new_password': 'New Password',
    'change_password': 'Change Password',
    'send_login_link': 'Send Login Link'
}

_default_messages = {
    'UNAUTHORIZED': (
        'You do not have permission to view this resource.', 'error'),
    'CONFIRM_REGISTRATION': (
        'Thank you. Confirmation instructions have been sent to %(email)s.', 'success'),
    'EMAIL_CONFIRMED': (
        'Thank you. Your email has been confirmed.', 'success'),
    'ALREADY_CONFIRMED': (
        'Your email has already been confirmed.', 'info'),
    'INVALID_CONFIRMATION_TOKEN': (
        'Invalid confirmation token.', 'error'),
    'EMAIL_ALREADY_ASSOCIATED': (
        '%(email)s is already associated with an account.', 'error'),
    'PASSWORD_MISMATCH': (
        'Password does not match', 'error'),
    'RETYPE_PASSWORD_MISMATCH': (
        'Passwords do not match', 'error'),
    'INVALID_REDIRECT': (
        'Redirections outside the domain are forbidden', 'error'),
    'PASSWORD_RESET_REQUEST': (
        'Instructions to reset your password have been sent to %(email)s.', 'info'),
    'PASSWORD_RESET_EXPIRED': (
        'You did not reset your password within %(within)s. New instructions have been sent '
        'to %(email)s.', 'error'),
    'INVALID_RESET_PASSWORD_TOKEN': (
        'Invalid reset password token.', 'error'),
    'CONFIRMATION_REQUIRED': (
        'Email requires confirmation.', 'error'),
    'CONFIRMATION_REQUEST': (
        'Confirmation instructions have been sent to %(email)s.', 'info'),
    'CONFIRMATION_EXPIRED': (
        'You did not confirm your email within %(within)s. New instructions to confirm your email '
        'have been sent to %(email)s.', 'error'),
    'LOGIN_EXPIRED': (
        'You did not login within %(within)s. New instructions to login have been sent to '
        '%(email)s.', 'error'),
    'LOGIN_EMAIL_SENT': (
        'Instructions to login have been sent to %(email)s.', 'success'),
    'INVALID_LOGIN_TOKEN': (
        'Invalid login token.', 'error'),
    'DISABLED_ACCOUNT': (
        'Account is disabled.', 'error'),
    'EMAIL_NOT_PROVIDED': (
        'Email not provided', 'error'),
    'INVALID_EMAIL_ADDRESS': (
        'Invalid email address', 'error'),
    'PASSWORD_NOT_PROVIDED': (
        'Password not provided', 'error'),
    'PASSWORD_NOT_SET': (
        'No password is set for this user', 'error'),
    'PASSWORD_INVALID_LENGTH': (
        'Password must be at least 6 characters', 'error'),
    'USER_DOES_NOT_EXIST': (
        'Specified user does not exist', 'error'),
    'INVALID_PASSWORD': (
        'Invalid password', 'error'),
    'PASSWORDLESS_LOGIN_SUCCESSFUL': (
        'You have successfuly logged in.', 'success'),
    'PASSWORD_RESET': (
        'You successfully reset your password and you have been logged in automatically.', 'success'),
    'PASSWORD_IS_THE_SAME': (
        'Your new password must be different than your previous password.', 'error'),
    'PASSWORD_CHANGE': (
        'You successfully changed your password.', 'success'),
    'LOGIN': (
        'Please log in to access this page.', 'info'),
    'REFRESH': (
        'Please reauthenticate to access this page.', 'info'),
    }


class ValidatorMixin(object):

    def __call__(self, form, field):
        if self.message and self.message.isupper():
            self.message = _default_messages.get(self.message)[0]
        return super(ValidatorMixin, self).__call__(form, field)


class EqualTo(ValidatorMixin, validators.EqualTo):
    pass


class Required(ValidatorMixin, validators.Required):
    pass


class Email(ValidatorMixin, validators.Email):
    pass


class Length(ValidatorMixin, validators.Length):
    pass


email_required = Required(message='EMAIL_NOT_PROVIDED')
email_validator = Email(message='INVALID_EMAIL_ADDRESS')
password_required = Required(message='PASSWORD_NOT_PROVIDED')
password_length = Length(min=6, max=128, message='PASSWORD_INVALID_LENGTH')


def get_form_field_label(key):
    return _default_field_labels.get(key, '')


class Form(BaseForm):

    def __init__(self, *args, **kwargs):
        if current_app.testing:
            self.TIME_LIMIT = None
        super(Form, self).__init__(*args, **kwargs)


class UserEmailFormMixin():
    user = None
    email = EmailField(
        get_form_field_label('email'),
        validators=[email_required, email_validator])


class PasswordFormMixin():
    password = PasswordField(
        get_form_field_label('password'), validators=[password_required])


class NewPasswordFormMixin():
    password = PasswordField(
        get_form_field_label('password'),
        validators=[password_required, password_length])


class PasswordConfirmFormMixin():
    password_confirm = PasswordField(
        get_form_field_label('retype_password'),
        validators=[EqualTo('password', message='RETYPE_PASSWORD_MISMATCH')])


class SendConfirmationForm(Form, UserEmailFormMixin):

    """The default send confirmation email form"""

    submit = SubmitField(get_form_field_label('send_confirmation'))
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        super(SendConfirmationForm, self).__init__(*args, **kwargs)
        if request.method == 'GET':
            self.email.data = request.args.get('email', None)
        if not self.next.data:
            self.next.data = request.args.get('next', url_for('index'))


class ForgotPasswordForm(Form, UserEmailFormMixin):

    """The default forgot password form"""

    submit = SubmitField(get_form_field_label('recover_password'))


class LoginForm(Form):

    """The default login form"""

    email = EmailField(get_form_field_label('email'), [validators.DataRequired()])
    password = PasswordField(get_form_field_label('password'), [validators.DataRequired()])
    next = HiddenField()
    submit = SubmitField(get_form_field_label('login'))

    bad_email = False
    bad_password = False

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = request.args.get('next', url_for('index'))


class RegisterForm(Form, PasswordConfirmFormMixin):

    email = EmailField(get_form_field_label('email'), [validators.DataRequired()])
    password = PasswordField(get_form_field_label('password'), [validators.DataRequired()])
    next = HiddenField()
    submit = SubmitField(get_form_field_label('register'))

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = request.args.get('next', url_for('index'))


class ResetPasswordForm(Form, NewPasswordFormMixin, PasswordConfirmFormMixin):

    """The default reset password form"""

    submit = SubmitField(get_form_field_label('reset_password'))
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        super(ResetPasswordForm, self).__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = request.args.get('next', url_for('index'))


class ChangePasswordForm(Form, PasswordFormMixin):

    """The default change password form"""

    next = HiddenField()
    new_password = PasswordField(
        get_form_field_label('new_password'),
        validators=[password_required, password_length])

    new_password_confirm = PasswordField(
        get_form_field_label('retype_password'),
        validators=[
            EqualTo(
                'new_password',
                message='RETYPE_PASSWORD_MISMATCH')])

    submit = SubmitField(get_form_field_label('change_password'))

    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        if not self.next.data:
            self.next.data = request.args.get('next', url_for('index'))

class CorrectThisPageForm(Form):
    email = TextField('Email', [validators.Optional()])
    details = TextField('Details', [validators.Optional()])
    url = TextField('URL', [validators.Optional()])

    def save(self):
        pass

