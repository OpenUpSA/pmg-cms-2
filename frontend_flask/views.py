from flask import request, flash, make_response, url_for, session, render_template, abort, redirect
from frontend_flask import app, logger
import requests
from datetime import datetime, date
import urllib

API_HOST = app.config['API_HOST']
error_bad_request = 400


class ApiException(Exception):
    """
    Class for handling all of our expected API errors.
    """

    def __init__(self, status_code, message):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        rv = {
            "code": self.status_code,
            "message": self.message
        }
        return rv


@app.errorhandler(ApiException)
def handle_api_exception(error):
    """
    Error handler, used by flask to pass the error on to the user, rather than catching it and throwing a HTTP 500.
    """

    logger.debug(error)
    logger.debug(request.path)
    logger.debug(urllib.quote_plus(request.path))
    flash(error.message + " (" + str(error.status_code) + ")", "danger")
    # catch 'Unauthorised' status
    if error.status_code == 401:
        session.clear()
        return redirect(url_for('login') + "?next=" + urllib.quote_plus(request.path))
    return redirect(url_for('landing'))


def load_from_api(resource_name, resource_id=None, page=None):

    query_str = resource_name + "/"
    if resource_id:
        query_str += str(resource_id) + "/"
    if page:
        query_str += "?page=" + str(page)

    headers = {}
    # add auth header
    if session and session.get('api_key'):
        headers = {'Authorization': 'ApiKey:' + session.get('api_key')}
    try:
        response = requests.get(API_HOST + query_str, headers=headers)
        out = response.json()
        if response.status_code != 200:
            raise ApiException(response.status_code, response.json().get('message', "An unspecified error has occurred."))
        i = 0
        return out

    except requests.ConnectionError:
        flash('Error connecting to backend service.', 'danger')
        pass
    return


@app.route('/')
def index():
    """

    """

    logger.debug("index page called")

    return render_template('index.html')


@app.route('/bills/')
def bills():
    """
    Page through all available bills.
    """

    logger.debug("bills page called")

    return render_template('bill_list.html')


@app.route('/committees/')
def committees():
    """
    Page through all available committees.
    """

    logger.debug("committees page called")

    return render_template('committee_list.html')


@app.route('/committee/<int:committee_id>/')
def committee_detail(committee_id=None):
    """
    Display all available detail for ta committee.
    """

    logger.debug("committee detail page called")
    committee = load_from_api('committee', committee_id)
    return render_template('committee_detail.html', committee=committee)
