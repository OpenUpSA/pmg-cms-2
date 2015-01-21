from flask import render_template, g, request, redirect, session, url_for, abort, flash
from frontend import app
from views import ApiException, load_from_api
import os
import forms
import requests
from requests import ConnectionError
import json
import logging

API_HOST = app.config['API_HOST']
logger = logging.getLogger(__name__)


# chat with backend API
def user_management_api(endpoint, data=None):

    query_str = "security/" + endpoint

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    if endpoint != 'login' and session and session.get('api_key'):
        headers['Authentication-Token'] = session['api_key']
    try:
        response = requests.post(
            API_HOST +
            query_str,
            data=data,
            headers=headers,
            allow_redirects=False)
        try:
            out = response.json()
            if response.status_code != 200:
                raise ApiException(
                    response.status_code,
                    out.get(
                        'message',
                        u"An unspecified error has occurred."))
            if out.get('response') and out['response'].get('errors'):
                for field, messages in out['response']['errors'].iteritems():
                    for message in messages:
                        flash(message, 'danger')
        except ValueError:
            logger.error("Error interpreting response from API. No JSON object could be decoded")
            flash(u"Error interpreting response from API.", 'danger')
            logger.debug(response.text)
            return
        try:
            logger.debug(json.dumps(out, indent=4))
        except Exception:
            logger.debug("Error logging response from API")
        return out['response']

    except ConnectionError:
        flash(u'Error connecting to backend service.', 'danger')
        pass
    return


@app.route('/login/', methods=['GET', 'POST'])
def login():
    """View function for login view"""

    form = forms.LoginForm(request.form)
    if request.args.get('next'):
        form.next.data = request.args['next']

    if form.validate_on_submit():
        data = {
            'email': form.email.data,
            'password': form.password.data
        }
        response = user_management_api('login', json.dumps(data))

        # save auth token
        if response and response.get('user') and response['user'].get('authentication_token'):
            session['api_key'] = response['user']['authentication_token']
            update_current_user()

            if request.values.get('next'):
                return redirect(request.values['next'])

    return render_template('user_management/login_user.html', form=form)


@app.route('/logout/', methods=['GET', ])
def logout():
    """View function which handles a logout request."""

    response = user_management_api('logout')
    session.clear()
    if response:
        flash(u'You have been logged out successfully.', 'success')
        return redirect(request.args.get('next', None) or
                        url_for('index'))
    return redirect(url_for('index'))


@app.route('/register/', methods=['GET', 'POST'])
def register():
    """View function which handles a registration request."""

    form = forms.RegisterForm(request.form)
    if request.args.get('next'):
        form.next.data = request.args['next']

    if form.validate_on_submit():
        data = {
            'email': form.email.data,
            'password': form.password.data
        }
        response = user_management_api('register', json.dumps(data))

        # save Api Key and redirect user
        if response and response.get('user') and response['user'].get('authentication_token'):
            logger.debug("saving authentication_token to the session")
            session['api_key'] = response['user']['authentication_token']
            update_current_user()
            flash(
                u'You have been registered. Please check your email for a confirmation.',
                'success')
            if request.values.get('next'):
                return redirect(request.values['next'])

    return render_template('user_management/register_user.html', form=form)


@app.route('/send-confirmation/', methods=['GET', 'POST'])
def send_confirmation():
    """View function which sends confirmation instructions."""

    form = forms.SendConfirmationForm(request.form)

    if form.validate_on_submit():
        data = {
            'email': form.email.data,
        }
        response = user_management_api('confirm', json.dumps(data))

        # redirect user
        if response and response.get('user'):
            flash(
                u'Your confirmation email has been resent. Please check your inbox.',
                'success')
            if request.values.get('next'):
                return redirect(request.values['next'])

    return render_template(
        'user_management/send_confirmation.html',
        send_confirmation_form=form)


@app.route('/forgot-password/', methods=['GET', 'POST'])
def forgot_password():
    """View function that handles a forgotten password request."""

    form = forms.ForgotPasswordForm(request.form)

    if form.validate_on_submit():
        data = {
            'email': form.email.data,
        }
        response = user_management_api('reset', json.dumps(data))
        # redirect user
        if response and not response.get('errors'):
            flash(
                u'You will receive an email with instructions for resetting your password. Please check your inbox.',
                'success')
            if request.values.get('next'):
                return redirect(request.values['next'])

    return render_template(
        'user_management/forgot_password.html',
        forgot_password_form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """View function that handles a reset password request."""

    form = forms.ResetPasswordForm()

    if form.validate_on_submit():
        data = {
            "password": form.password.data,
            "password_confirm": form.password_confirm.data,
        }
        response = user_management_api('reset/' + token, json.dumps(data))

        if response and not response.get('errors'):
            flash(u'Your password has been changed successfully.', 'success')
            logger.debug("saving authentication_token to the session")
            session['api_key'] = response['user']['authentication_token']
            update_current_user()
            # redirect user
            if request.values.get('next'):
                return redirect(request.values['next'])
            else:
                return redirect(url_for('index'))

    return render_template(
        'user_management/reset_password.html',
        reset_password_form=form,
        reset_password_token=token)


@app.route('/change-password/', methods=['GET', 'POST'])
def change_password():
    """View function which handles a change password request."""

    form = forms.ChangePasswordForm()

    if form.validate_on_submit():
        data = {
            "password": form.password.data,
            "new_password": form.new_password.data,
            "new_password_confirm": form.new_password_confirm.data,
        }
        response = user_management_api('change', json.dumps(data))
        # redirect user
        if response and not response.get('errors'):
            flash(u'Your password has been changed successfully.', 'success')
            if request.values.get('next'):
                return redirect(request.values['next'])

    return render_template(
        'user_management/change_password.html',
        change_password_form=form)


@app.route('/confirm-email/<confirmation_key>', methods=['GET', ])
def confirm_email(confirmation_key):
    """View function for confirming an email address."""

    response = user_management_api('confirm/' + confirmation_key)

    if response and not response.get('errors'):
        flash(u'Thanks. Your email address has been confirmed.', 'success')
    return redirect(url_for('index'))


def update_current_user():
    """
    Hit the API, and update our session's 'current_user' if necessary.
    """

    tmp = load_from_api("")  # hit the API's index page
    if tmp.get('current_user'):
        session['current_user'] = tmp['current_user']
    return