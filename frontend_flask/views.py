from flask import request, make_response, url_for, session, render_template, abort, redirect
from frontend_flask import app, logger
import requests
from datetime import datetime, date

API_HOST = app.config['API_HOST']
error_bad_request = 400


def url(action, param=None):
    u = "http://{host}/{action}/".format(host=API_HOST, action=action)
    if param:
        return u + param + "/"
    return u


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

    # api_url = url("committee", str(committee))
    # r = requests.get(api_url)
    # if not r.status_code == 200:
    #     return(r.text, r.status_code)
    # committee = r.json()
    committee = None

    return render_template('committee_detail.html', committee=committee)
