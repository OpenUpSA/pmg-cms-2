import logging
import requests
import urllib

from flask import flash, session, abort, redirect, url_for, request
from werkzeug.exceptions import HTTPException
from flask.ext.security import current_user

from pmg import app

API_HOST = app.config['API_HOST']

logger = logging.getLogger(__name__)

class ApiException(HTTPException):
    """
    Class for handling all of our expected API errors.
    """

    def __init__(self, status_code, message):
        super(ApiException, self).__init__(message)
        self.code = status_code
        self.message = self.description

    def get_response(self, environ=None):
        logger.error("API error: %s" % self.description)
        flash(self.description + " (" + str(self.code) + ")", "danger")

        if self.code == 401:
            session.clear()
            return redirect(url_for('login') + "?next=" + urllib.quote_plus(request.path))

        return super(ApiException, self).get_response(environ)

    def get_body(self, environ):
        return render_template('500.html', error=self)




def load_from_api(resource_name, resource_id=None, page=None, return_everything=False, params=None):
    params = {} if (params is None) else params

    query_str = resource_name + "/"
    if resource_id:
        query_str += str(resource_id) + "/"
    if page:
        params["page"] = str(page)

    headers = {}
    # add auth header
    if current_user.is_authenticated():
        headers = {'Authentication-Token': current_user.get_auth_token()}

    try:
        response = requests.get(API_HOST + query_str, headers=headers, params=params)

        if response.status_code == 404:
            abort(404)

        if response.status_code != 200 and response.status_code not in [401, 403]:
            try:
                msg = response.json().get('message')
            except Exception:
                msg = None

            raise ApiException(response.status_code, msg or "An unspecified error has occurred.")

        out = response.json()
        if return_everything:
            next_response_json = out
            i = 0
            while next_response_json.get('next') and i < 1000:
                next_response = requests.get(next_response_json.get('next'), headers=headers, params=params)
                next_response_json = next_response.json()
                out['results'] += next_response_json['results']
                i += 1
            if out.get('next'):
                out.pop('next')

        return out
    except requests.ConnectionError as e:
        logger.error("Error connecting to backend service: %s" % e, exc_info=e)
        flash(u'Error connecting to backend service.', 'danger')


def send_to_api(endpoint, data=None):

    query_str = endpoint + "/"

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    # add auth header
    if session and session.get('api_key'):
        headers['Authentication-Token'] = session.get('api_key')
    try:
        response = requests.post(
            API_HOST +
            query_str,
            headers=headers,
            data=data)
        out = response.json()

        if response.status_code != 200:
            try:
                msg = response.json().get('message')
            except Exception:
                msg = None

            raise ApiException(
                response.status_code,
                msg or "An unspecified error has occurred.")
        return out
    except requests.ConnectionError:
        flash('Error connecting to backend service.', 'danger')
