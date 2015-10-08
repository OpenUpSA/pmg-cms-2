import os
import forms
import requests
from requests import ConnectionError
import json
import logging
from ga import ga_event

from flask import render_template, g, request, redirect, session, url_for, abort, flash, jsonify
from flask.ext.security import login_user, current_user
from flask.ext.security.decorators import anonymous_user_required

from pmg import app, db
from pmg.api_client import ApiException, load_from_api, send_to_api
from pmg.models import Committee, SavedSearch
from pmg.models.users import security

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


@app.route('/confirm-email/<confirmation_key>', methods=['GET', ])
@anonymous_user_required
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
    next_url = request.values.get('next', '')

    if current_user.is_authenticated() and request.method == 'POST':
        ids = request.form.getlist('committees')
        current_user.committee_alerts = Committee.query.filter(Committee.id.in_(ids)).all()
        current_user.subscribe_daily_schedule = bool(request.form.get('subscribe_daily_schedule'))

        db.session.commit()

        # register a google analytics event
        ga_event('user', 'change-alerts')
        flash("Your notification settings have been updated successfully.", "success")
        if next_url:
            return redirect(next_url)

        return redirect(url_for('email_alerts'))

    committees = load_from_api('committee', return_everything=True)['results']
    if current_user.is_authenticated():
        subscriptions = set(c.id for c in current_user.committee_alerts)
    else:
        subscriptions = set()

    return render_template('user_management/email_alerts.html',
            committees=committees,
            after_signup=bool(next_url),
            subscriptions=subscriptions,
            next_url=next_url)


@app.route('/user/alerts/committees/<int:committee_id>', methods=['POST'])
def user_committee_alert(committee_id):
    if current_user.is_authenticated() and request.method == 'POST':
        current_user.committee_alerts.append(Committee.query.get(committee_id))
        db.session.commit()
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


@app.route('/user/saved-search/', methods=['POST'])
def create_search():
    saved_search = SavedSearch.find_or_create(
        current_user,
        request.form.get('q'),
        content_type=request.form.get('content_type') or None,
        committee_id=request.form.get('committee_id') or None)

    db.session.commit()

    return jsonify(id=saved_search.id)


@app.route('/user/saved-search/<int:id>/delete', methods=['POST'])
def remove_search(id):
    saved_search = SavedSearch.query.get(id)
    if not saved_search:
        abort(404)
    db.session.delete(saved_search)
    db.session.commit()

    return ''
