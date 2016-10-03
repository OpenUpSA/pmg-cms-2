import logging
import requests
import urllib

from flask import flash, session, abort, redirect, url_for, request, render_template
from werkzeug.exceptions import HTTPException
from flask.ext.security import current_user

from pmg import app

API_HOST = app.config['API_HOST']
# timeout connecting and reading from remote host
TIMEOUTS = (3.05, 10)

logger = logging.getLogger(__name__)

# Disable urllib3 warnings
# https://urllib3.readthedocs.org/en/latest/security.html#insecurerequestwarning
requests.packages.urllib3.disable_warnings()


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


def load_from_api(resource_name, resource_id=None, page=None, return_everything=False, fields=None, params=None):
    """ Load data from the PMG API.

    :param str resource_name: resource to load (used as the start of the URL)
    :param int resource_id: resource id (optional), appended to the resource name
    :param int page: page number to load (default is the first page)
    :param bool return_everything: fetch all pages? (default: False)
    :param list fields: list of field names to ask for (V2 only).
    :param dict params: additional query params
    """
    params = {} if (params is None) else params
    v2 = resource_name.startswith('v2')

    if fields and not v2:
        raise ValueError("Fields parameter is only supported for API v2 urls.")

    query_str = resource_name
    if resource_id:
        query_str += "/" + str(resource_id)
    if not v2:
        query_str += '/'

    if page:
        params["page"] = str(page)
    if fields:
        params["fields"] = ','.join(fields)

    headers = {}
    # add auth header
    if current_user.is_authenticated():
        headers = {'Authentication-Token': current_user.get_auth_token()}

    try:
        response = requests.get(API_HOST + query_str, headers=headers, params=params, timeout=TIMEOUTS)

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
                next_response = requests.get(next_response_json.get('next'), headers=headers, params=params, timeout=TIMEOUTS)
                next_response_json = next_response.json()
                out['results'] += next_response_json['results']
                i += 1
            if out.get('next'):
                out.pop('next')

        return out
    except requests.ConnectionError as e:
        logger.error("Error connecting to backend service: %s" % e, exc_info=e)
        flash(u'Error connecting to backend service.', 'danger')
