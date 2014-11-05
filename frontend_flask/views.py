from flask import request, flash, make_response, url_for, session, render_template, abort, redirect
from frontend_flask import app, logger
import requests
from datetime import datetime, date
import dateutil.parser
import urllib
from search.search import Search
import math

API_HOST = app.config['API_HOST']
error_bad_request = 400


@app.template_filter('pretty_date')
def _jinja2_filter_datetime(iso_str):

    format='%d %b %Y'
    date = dateutil.parser.parse(iso_str)
    return date.strftime(format)


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


def load_from_api(resource_name, resource_id=None, page=None, return_everything=False):

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
        if return_everything:
            next_response_json = out
            i = 0
            while next_response_json.get('next') and i < 1000:
                next_response = requests.get(next_response_json.get('next'), headers=headers)
                next_response_json = next_response.json()
                out['results'] += next_response_json['results']
                i += 1
            if out.get('next'):
                out.pop('next')
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
    committee_list = load_from_api('committee', return_everything=True)
    committees = committee_list['results']
    return render_template('committee_list.html', committees=committees)


@app.route('/committee/<int:committee_id>/')
def committee_detail(committee_id):
    """
    Display all available detail for the committee.
    """

    logger.debug("committee detail page called")
    committee = load_from_api('committee', committee_id)
    return render_template('committee_detail.html', committee=committee)


@app.route('/committee-meeting/<int:event_id>/')
def committee_meeting(event_id):
    """
    Display committee meeting details, including report and any other related content.
    """

    logger.debug("committee meeting page called")
    event = load_from_api('committee-meeting', event_id)
    related_docs = []
    audio = []
    for item in event.get('content'):
        if item['type'] == "committee-meeting-report":
            body = item['body']
            summary = item['summary']
            pass
        elif "audio" in item['type']:
            audio.append(item)
        else:
            related_docs.append(item)

    return render_template('committee_meeting.html', summary=summary, body=body, event=event, audio=audio, related_docs=related_docs, STATIC_HOST=app.config['STATIC_HOST'])


@app.route('/bill/<int:bill_id>/')
def bill(bill_id):
    """
    With Bills, we try to send them to BillTracker if it exists. Else we serve the PDF. If that doesn't work, we Kill Bill
    """

    logger.debug("bill page called")
    bill =  load_from_api('bill', bill_id)
    if ("code" in bill):
        logger.debug("found bill code", bill["code"])
    else:
        if ("files" in bill):
            logger.debug(bill["files"][0])
            return redirect(bill["files"][0]["url"], code=302)
    logger.debug(bill)
    return "Oh dear"

@app.route('/member/<int:member_id>')
def member(member_id):
    logger.debug("member page called")
    member =  load_from_api('member', member_id)
    return render_template('member_detail.html', member=member, STATIC_HOST=app.config['STATIC_HOST'])

@app.route('/hansard/<int:hansard_id>')
def hansard(hansard_id):
    logger.debug("hansard page called")
    hansard =  load_from_api('hansard', hansard_id)
    return render_template('hansard_detail.html', hansard=hansard, STATIC_HOST=app.config['STATIC_HOST'])

@app.route('/search/')
def search():
    """
    Display search page
    """
    search = Search()
    q = request.args.get('q')
    logger.debug("search page called")
    page = 0
    if (request.args.get('page')):
        page = int(request.args.get('page'))
    per_page = 20
    if (request.args.get('per_page')):
        per_page = int(request.args.get('per_page'))
    searchresult = search.search(q, per_page, page * per_page)
    result = {}
    result = searchresult["hits"]["hits"]
    count = searchresult["hits"]["total"]
    max_score = searchresult["hits"]["max_score"]
    logger.debug("Pages %i", math.ceil(count / per_page))
    search_url = request.url_root + "search/?q=" + q + "&per_page=" + str(per_page)
    # if count > (page + 1) * per_page:
        # result["next"] = request.url_root + "search/?q=" + q + "&page=" + str(page+1) + "&per_page=" + str(per_page)
        # result["last"] = request.url_root + "search/?q=" + q + "&page=" + str(int(math.ceil(count / per_page))) + "&per_page=" + str(per_page)
        # result["first"] = request.url_root + "search/?q=" + q + "&page=0" + "&per_page=" + str(per_page)
    num_pages = int(math.ceil(float(count) / float(per_page)))
    return render_template('search.html', STATIC_HOST=app.config['STATIC_HOST'], results=result, count=count, num_pages=num_pages, page=page,per_page=per_page, search_url = search_url)
