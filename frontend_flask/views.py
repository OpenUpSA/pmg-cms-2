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


# @app.route('/bill/<bill_id>/')
# def detail(bill_id=None):
#     """
#     Display all available detail for the requested bill.
#     """
#
#     try:
#         bill_id = int(bill_id)
#     except:
#         abort(error_bad_request)
#
#     logger.debug("detail page called")
#     api_url = url("bill", str(bill_id))
#     r = requests.get(api_url)
#     if not r.status_code == 200:
#         return(r.text, r.status_code)
#     bill = r.json()
#
#     entries = bill["entries"]
#
#     # separate special entries from the rest of the list
#     version_types = ["bill-version", "act"]
#     special_types = ["original-act", "gazette", "whitepaper", "memorandum", "greenpaper", "draft"]
#
#     bill["entries"] = [entry for entry in entries if entry["type"] not in version_types + special_types]
#
#     bill["versions"] = [entry for entry in entries if entry["type"] in version_types]
#     special_entries = [entry for entry in entries if entry["type"] in special_types]
#     for entry in special_entries:
#         bill[entry["type"]] = entry
#
#     return render_template('detail.html', bill=bill)
