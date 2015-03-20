import os
import forms
import requests
from requests import ConnectionError
import json
import logging
from ga import ga_event

from flask import render_template, g, request, redirect, session, url_for, abort, flash
from flask.ext.security import login_user, current_user

from frontend import app
from frontend.api import ApiException, load_from_api, send_to_api
from backend.models.users import security

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
        response = requests.post(API_HOST + query_str, data=data, headers=headers, allow_redirects=False)
        try:
            out = response.json()
            if response.status_code != 200:
                raise ApiException(response.status_code,
                                   out.get('message', u"An unspecified error has occurred."))

            if out.get('response', {}).get('errors'):
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

    except ConnectionError as e:
        logger.error("Error connecting to backend service: %s" % e, exc_info=e)
        flash(u'Error connecting to backend service.', 'danger')


@app.route('/user/register/', methods=['GET', 'POST'])
def register():
    """View function which handles a registration request."""
    if g.current_user:
        return redirect(request.args.get('next', '/'))

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
            load_current_user()

            # set a google analytics event that will be sent when the page loads
            ga_event('user', 'register')
            flash(u'You have been registered. Please check your email for a confirmation.', 'success')

            return redirect(url_for('email_alerts', next=request.values.get('next', '/')))

    return render_template('user_management/register_user.html', form=form)


@app.route('/user/send-confirmation/', methods=['GET', 'POST'])
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


@app.route('/user/forgot-password/', methods=['GET', 'POST'])
def forgot_password():
    """View function that handles a forgotten password request."""

    form = forms.ForgotPasswordForm(request.form)

    if form.validate_on_submit():
        data = {
            'email': form.email.data,
        }
        response = user_management_api('reset', json.dumps(data))
        # redirect user
        if not response or not response.get('errors'):
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
            load_current_user()
            # redirect user
            if request.values.get('next'):
                return redirect(request.values['next'])
            else:
                return redirect(url_for('index'))

    return render_template(
        'user_management/reset_password.html',
        reset_password_form=form,
        reset_password_token=token)


@app.route('/user/change-password/', methods=['GET', 'POST'])
def change_password():
    """View function which handles a change password request."""
    if not g.current_user:
        return redirect(url_for('login', next=request.url))

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



@app.route('/email-alerts/', methods=['GET', 'POST'])
def email_alerts():
    """
    Allow a user to manage their notification alerts.
    """
    committees = None
    next_url = request.values.get('next', '')

    if g.current_user and request.method == 'POST':
        out = {'committee_alerts': [], 'general_alerts': []}
        general_notifications = ['select-daily-schedule']

        for field_name in request.form.keys():
            if field_name in ['csrf_token', 'next']:
                continue

            if field_name in general_notifications:
                key = "-".join(field_name.split('-')[1::])
                out['general_alerts'].append(key)
            else:
                committee_id = int(field_name.split('-')[-1])
                out['committee_alerts'].append(committee_id)
        tmp = send_to_api('update_alerts', json.dumps(out))
        if tmp:
            # register a google analytics event
            ga_event('user', 'change-alerts')
            flash("Your notification settings have been updated successfully.", "success")
            if next_url:
                return redirect(next_url)
            return redirect(url_for('email_alerts'))

    committees = load_from_api('committee', return_everything=True)['results']
    return render_template('user_management/email_alerts.html',
            committees=committees,
            after_signup=bool(next_url),
            next_url=next_url)


@app.route('/user/alerts/committees/<int:committee_id>', methods=['POST'])
def user_committee_alert(committee_id):
    res = send_to_api('user/alerts/committees/%s' % committee_id)
    if res.get('alerts'):
        ga_event('user', 'add-alert', 'cte-alert-box')
        flash("We'll send you email alerts for updates on this committee.", 'success')
    return redirect(request.values.get('next', '/'))


@app.route('/committee-subscriptions/', methods=['GET', 'POST'])
def committee_subscriptions():
    """
    Manage subscriptions to premium content.
    """

    premium_committees = load_from_api('committee/premium', return_everything=True)['results']
    return render_template('user_management/committee_subscriptions.html', premium_committees=premium_committees)
