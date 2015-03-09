import logging
from datetime import datetime, date
import dateutil.parser
import urllib
import math
import random
import re
import json
import os.path

from flask import request, flash, make_response, url_for, session, render_template, abort, redirect, g
from werkzeug.exceptions import HTTPException
import requests
import arrow

from frontend import app
from frontend.bills import bill_history, MIN_YEAR

API_HOST = app.config['API_HOST']
error_bad_request = 400
app.session = session

logger = logging.getLogger(__name__)


def admin_url(model_name, id):
    return API_HOST.replace('http', 'https') + 'admin/%s/edit/?id=%s' % (model_name, id)


@app.template_filter('pretty_date')
def _jinja2_filter_datetime(iso_str, format_option=None):
    if not iso_str:
        return ""
    format = '%d %b %Y'
    if format_option == "long":
        format = '%d %B %Y'
    date = dateutil.parser.parse(iso_str)
    return date.strftime(format)


@app.template_filter('member_url')
def _jinja2_filter_member_url(member):
    if member.get('pa_url'):
        return member['pa_url']
    return url_for('member', member_id=member['id'])


@app.template_filter('search_snippet')
def _jinja2_filter_search_snippet(snippet):
    if not snippet:
        return ""
    if isinstance(snippet, list):
        snippet = ' ... '.join(snippet)
    return snippet


@app.template_filter('ellipse')
def _jinja2_filter_ellipse(snippet):
    return "...&nbsp;" + snippet.strip() + "&nbsp;..."


@app.template_filter('nbsp')
def _jinja2_nbsp(str):
    return str.replace(" ", "&nbsp;")


@app.template_filter('human_date')
def _jinja2_filter_humandate(iso_str):
    if not iso_str:
        return ""
    return arrow.get(iso_str).humanize()


@app.context_processor
def pagination_processor():
    def pagination(page_count, current_page, per_page, url):
        # Source:
        # https://github.com/jmcclell/django-bootstrap-pagination/blob/master/bootstrap_pagination/templatetags/bootstrap_pagination.py#L154
        range_length = 15
        logger.debug("Building pagination")
        if range_length is None:
            range_min = 1
            range_max = page_count
        else:
            if range_length < 1:
                raise Exception(
                    "Optional argument \"range\" expecting integer greater than 0")
            elif range_length > page_count:
                range_length = page_count
            range_length -= 1
            range_min = max(current_page - (range_length / 2) + 1, 1)
            range_max = min(current_page + (range_length / 2) + 1, page_count)
            range_diff = range_max - range_min
            if range_diff < range_length:
                shift = range_length - range_diff
                if range_min - shift > 0:
                    range_min -= shift
                else:
                    range_max += shift
        page_range = range(range_min, range_max + 1)
        s = ""
        for i in page_range:
            active = ""
            if ((i - 1) == current_page):
                active = "active"
            query_string = ""
            if (request.query_string):
                query_string = "?" + request.query_string
            s += "<li class='{0}'><a href='{1}/{2}/{4}'>{3}</a></li>".format(
                active,
                url,
                i -
                1,
                i,
                query_string)
        return s
    return dict(pagination=pagination)


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



@app.errorhandler(404)
def page_not_found(error):
    tmp = send_to_api('check_redirect', json.dumps({'url': request.path}))
    if tmp and tmp.get('redirect'):
        target = tmp.get('redirect')

        logger.info("Legacy redirect from %s to %s" % (request.path, target))
        return redirect(target, code=302)

    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html', error=error), 500


def load_from_api(resource_name, resource_id=None, page=None, return_everything=False, params=None):
    params = {} if (params is None) else params

    query_str = resource_name + "/"
    if resource_id:
        query_str += str(resource_id) + "/"
    if page:
        params["page"] = str(page)

    headers = {}
    # add auth header
    if session and session.get('api_key'):
        headers = {'Authentication-Token': session.get('api_key')}

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
        pass
    return


@app.route('/')
def index():
    committee_meetings_api = load_from_api('committee-meeting')
    committee_meetings = []
    for committee_meeting in committee_meetings_api["results"]:
        if committee_meeting.get('committee'):
            committee_meetings.append(committee_meeting)
            if len(committee_meetings) == 10:
                break
    bills = load_from_api('bill')["results"][:10]
    schedule = load_from_api('schedule')["results"]
    scheduledates = []
    curdate = False
    for item in schedule:
        if item["meeting_date"] != curdate:
            curdate = item["meeting_date"]
            scheduledates.append(curdate)
    stock_pic = random.choice(["ncop.jpg", "na.jpg"])

    featured_content = load_from_api('featured')

    return render_template(
        'index.html',
        committee_meetings=committee_meetings,
        bills=bills,
        schedule=schedule,
        scheduledates=scheduledates,
        stock_pic=stock_pic,
        featured_content=featured_content)


@app.route('/bills/')
def bills_portal():
    return render_template('bills/index.html')


@app.route('/bills/explained/')
def bills_explained():
    return render_template('bills/explained.html')


@app.route('/bills/<any(current):bill_type>/')
@app.route('/bills/<any(all, draft, pmb, tabled):bill_type>/')
@app.route('/bills/<any(all, draft, pmb, tabled):bill_type>/year/<int:year>/')
def bills(bill_type, year=None):
    if bill_type == 'current':
        # don't paginate by year
        year_list = None
        params = {}

    else:
        year_list = range(MIN_YEAR, date.today().year+1)
        year_list.reverse()
        params = {}

        if not year:
            return redirect(url_for('bills', bill_type=bill_type, year=year_list[0]))

        if year not in year_list:
            abort(404)
        params = 'filter[year]=%d' % year

    api_url = 'bill' if bill_type == 'all' else 'bill/%s' % bill_type
    bills = load_from_api(api_url, return_everything=True, params=params)['results']

    status_dict = {
        "na": ("in progress", "label-primary"),
        "ncop": ("in progress", "label-primary"),
        "assent": ("submitted to the president", "label-warning"),
        "enacted": ("signed into law", "label-success"),
        "withdrawn": ("withdrawn", "label-default"),
        "lapsed": ("lapsed", "label-default"),
        }

    return render_template(
        'bills/list.html',
        results=bills,
        status_dict=status_dict,
        year=year,
        year_list=year_list,
        bill_type=bill_type)


@app.route('/bill/<int:bill_id>')
@app.route('/bill/<int:bill_id>/')
def bill(bill_id):
    bill = load_from_api('bill', bill_id)
    history = bill_history(bill)
    return render_template('bills/detail.html', bill=bill, history=history,
                           admin_edit_url=admin_url('bill', bill_id))


@app.route('/committee/<int:committee_id>')
@app.route('/committee/<int:committee_id>/')
def committee_detail(committee_id):
    """
    Display all available detail for the committee.
    """

    logger.debug("committee detail page called")
    committee = load_from_api('committee', committee_id)
    return render_template('committee_detail.html',
                           committee=committee,
                           admin_edit_url=admin_url('committee', committee_id))


@app.route('/committees/')
def committees():
    """
    Page through all available committees.
    """

    logger.debug("committees page called")
    committee_list = load_from_api('committee', return_everything=True)
    committees = committee_list['results']
    return render_template('committee_list.html', committees=committees, )


@app.route('/committee-meetings/')
@app.route('/committee-meetings/<int:page>/')
def committee_meetings(page=0):
    """
    Page through all available committee meetings.
    """
    committees = load_from_api('committee', return_everything=True)['results']
    filters = {'committee': None}
    params = {}

    if request.args.get('filter[committee]'):
        filters["committee"] = params['filter[committee_id]'] = request.args.get('filter[committee]')

    committee_meetings_list = load_from_api('committee-meeting', page=page, params=params)
    committee_meetings = committee_meetings_list['results']
    count = committee_meetings_list["count"]

    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    url = "/committee-meetings"
    return render_template(
        'list.html',
        results=committee_meetings,
        num_pages=num_pages,
        page=page,
        url=url,
        title="Committee Meeting Reports",
        content_type="committee-meeting",
        icon="comment",
        committees=committees,
        filters=filters)


@app.route('/committee-meeting/<int:event_id>')
@app.route('/committee-meeting/<int:event_id>/')
def committee_meeting(event_id):
    """
    Display committee meeting details, including report and any other related content.
    """

    event = load_from_api('committee-meeting', event_id)

    if event.get('premium_content_excluded'):
        premium_committees = load_from_api('committee/premium', return_everything=True)['results']
    else:
        premium_committees = None

    report = None
    related_docs = []
    audio = []
    if event.get('content'):
        for item in event['content']:
            if "audio" in item['type']:
                audio.append(item)
            elif item['type'] == "committee-meeting-report":
                report = item
            else:
                related_docs.append(item)

    return render_template(
        'committee_meeting.html',
        event=event,
        report=report,
        audio=audio,
        related_docs=related_docs,
        premium_committees=premium_committees,
        admin_edit_url=admin_url('committee_meeting', event_id))


@app.route('/tabled-committee-reports/')
@app.route('/tabled-committee-reports/<int:page>/')
def tabled_committee_reports(page=0):
    """
    Page through all available tabled-committee-reports.
    """

    logger.debug("tabled-committee-reports page called")
    committee_list = load_from_api('committee', return_everything=True)
    committees = committee_list['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    tabled_committee_reports_list = load_from_api(
        'tabled_committee_report',
        page=page,
        params=params)
    count = tabled_committee_reports_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    tabled_committee_reports = tabled_committee_reports_list['results']
    url = "/tabled-committee-reports"
    return render_template(
        'list.html',
        results=tabled_committee_reports,
        content_type="tabled_committee_report",
        title="Tabled Committee Reports",
        num_pages=num_pages,
        page=page,
        url=url,
        icon="briefcase",
        committees=committees,
        filters=filters)


@app.route('/tabled-committee-report/<int:tabled_committee_report_id>')
@app.route('/tabled-committee-report/<int:tabled_committee_report_id>/')
def tabled_committee_report(tabled_committee_report_id):
    """
    Tabled Committee Report
    """
    logger.debug("tabled-committee-report page called")
    tabled_committee_report = load_from_api(
        'tabled_committee_report',
        tabled_committee_report_id)
    logger.debug(tabled_committee_report)
    return render_template(
        'tabled_committee_report_detail.html',
        tabled_committee_report=tabled_committee_report,
        admin_edit_url=admin_url('tabled_report', tabled_committee_report_id))

@app.route('/calls-for-comments/')
@app.route('/calls-for-comments/<int:page>/')
def calls_for_comments(page=0):
    """
    Page through all available calls-for-comments.
    """

    logger.debug("calls-for-comments page called")
    committee_list = load_from_api('committee', return_everything=True)
    committees = committee_list['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    call_for_comment_list = load_from_api(
        'call_for_comment',
        page=page,
        params=params)
    count = call_for_comment_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    calls_for_comments = call_for_comment_list['results']
    url = "/calls-for-comments"
    return render_template(
        'list.html',
        results=calls_for_comments,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="comments",
        content_type="call_for_comment",
        title="Calls for Comments",
        committees=committees,
        filters=filters)


@app.route('/call-for-comment/<int:call_for_comment_id>')
@app.route('/call-for-comment/<int:call_for_comment_id>/')
def call_for_comment(call_for_comment_id):
    """
    Tabled Committee Report
    """
    logger.debug("call-for-comment page called")
    call_for_comment = load_from_api(
        'call_for_comment',
        call_for_comment_id)
    logger.debug(call_for_comment)
    return render_template(
        'call_for_comment_detail.html',
        call_for_comment=call_for_comment,
        admin_edit_url=admin_url('call_for_comment', call_for_comment_id))


@app.route('/policy-documents/')
@app.route('/policy-documents/<int:page>/')
def policy_documents(page=0):
    """
    Page through all available policy-documents.
    """

    logger.debug("policy-documents page called")
    policy_documents_list = load_from_api('policy_document', page=page)
    count = policy_documents_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    policy_documents = policy_documents_list['results']
    url = "/policy-documents"
    return render_template(
        'list.html',
        results=policy_documents,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="file-text-o",
        content_type="policy_document",
        title="Policy Documents")


@app.route('/policy-document/<int:policy_document_id>')
@app.route('/policy-document/<int:policy_document_id>/')
def policy_document(policy_document_id):
    """
    Policy Document
    """
    logger.debug("policy-document page called")
    policy_document = load_from_api('policy_document', policy_document_id)
    logger.debug(policy_document)
    return render_template(
        'policy_document_detail.html',
        policy_document=policy_document,
        admin_edit_url=admin_url('policy', policy_document_id))


@app.route('/gazettes/')
@app.route('/gazettes/<int:page>/')
def gazettes(page=0):
    """
    Page through all available gazettes.
    """

    logger.debug("gazettes page called")
    gazettes_list = load_from_api('gazette', page=page)
    count = gazettes_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    gazettes = gazettes_list['results']
    url = "/gazettes"
    return render_template(
        'list.html',
        results=gazettes,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="file-text-o",
        content_type="gazette",
        title="Gazettes")


@app.route('/gazette/<int:gazette_id>')
@app.route('/gazette/<int:gazette_id>/')
def gazette(gazette_id):
    """
    Policy Document
    """
    logger.debug("gazette page called")
    gazette = load_from_api('gazette', gazette_id)
    logger.debug(gazette)
    return render_template(
        'gazette_detail.html',
        gazette=gazette,
        admin_edit_url=admin_url('gazette', gazette_id))


@app.route('/members/')
def members(page=0):
    """
    Page through all available members.
    """
    members = load_from_api('member', return_everything=True, page=page)['results']

    # partition by house
    members_by_house = {}
    for member in members:
        if member.get('house'):
            members_by_house.setdefault(member['house']['name'], []).append(member)
    colsize = 12 / len(members_by_house)

    return render_template('member_list.html', members_by_house=members_by_house, colsize=colsize)


@app.route('/member/<int:member_id>')
@app.route('/member/<int:member_id>/')
def member(member_id):
    logger.debug("member page called")
    member = load_from_api('member', member_id)
    return render_template(
        'member_detail.html',
        member=member,
        admin_edit_url=admin_url('member', member_id))


@app.route('/hansard/<int:event_id>')
@app.route('/hansard/<int:event_id>/')
def hansard(event_id):
    event = load_from_api('hansard', event_id)
    report = None
    related_docs = []
    audio = []
    if event.get('content'):
        for item in event['content']:
            if "audio" in item['type']:
                audio.append(item)
            elif item['type'] == "hansard":
                report = item
            else:
                related_docs.append(item)

    return render_template(
        'hansard_detail.html',
        event=event,
        report=report,
        audio=audio,
        related_docs=related_docs,
        admin_edit_url=admin_url('hansard', event_id))


@app.route('/hansards/')
@app.route('/hansards/<int:page>/')
def hansards(page=0):
    """
    Page through all available hansards.
    """

    logger.debug("hansards page called")
    hansards_list = load_from_api('hansard', page=page)
    count = hansards_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    hansards = hansards_list['results']
    url = "/hansards"
    return render_template(
        'list.html',
        results=hansards,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="archive",
        title="Hansards",
        content_type="hansard")


@app.route('/briefing/<int:event_id>')
@app.route('/briefing/<int:event_id>/')
def briefing(event_id):

    event = load_from_api('briefing', event_id)
    report = None
    related_docs = []
    audio = []
    if event.get('content'):
        for item in event['content']:
            if "audio" in item['type']:
                audio.append(item)
            elif item['type'] == "briefing":
                report = item
            else:
                related_docs.append(item)

    return render_template(
        'briefing_detail.html',
        event=event,
        report=report,
        audio=audio,
        related_docs=related_docs,
        admin_edit_url=admin_url('briefing', event_id))


@app.route('/briefings/')
@app.route('/briefings/<int:page>/')
def briefings(page=0):
    """
    Page through all available briefings.
    """

    logger.debug("briefings page called")
    briefings_list = load_from_api('briefing', page=page)
    count = briefings_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    briefings = briefings_list['results']
    url = "/briefings"
    return render_template(
        'list.html',
        results=briefings,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="bullhorn",
        title="Media Briefings",
        content_type="briefing",
        )


@app.route('/daily-schedule/<int:daily_schedule_id>')
@app.route('/daily-schedule/<int:daily_schedule_id>/')
def daily_schedule(daily_schedule_id):
    logger.debug("daily_schedule page called")
    daily_schedule = load_from_api('daily_schedule', daily_schedule_id)
    return render_template(
        'daily_schedule_detail.html',
        daily_schedule=daily_schedule,
        admin_edit_url=admin_url('schedule', daily_schedule_id))


@app.route('/daily-schedules/')
@app.route('/daily-schedules/<int:page>/')
def daily_schedules(page=0):
    """
    Page through all available daily_schedules.
    """

    logger.debug("daily_schedules page called")
    daily_schedules_list = load_from_api('daily_schedule', page=page)
    count = daily_schedules_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    daily_schedules = daily_schedules_list['results']
    url = "/daily_schedules"
    return render_template(
        'list.html',
        results=daily_schedules,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="calendar",
        title="Daily Schedules",
        content_type="daily_schedule")


@app.route('/question_reply/<int:question_reply_id>')
@app.route('/question_reply/<int:question_reply_id>/')
def question_reply(question_reply_id):
    logger.debug("question_reply page called")
    question_reply = load_from_api('question_reply', question_reply_id)
    return render_template(
        'question_reply_detail.html',
        question_reply=question_reply,
        admin_edit_url=admin_url('question', question_reply_id))


@app.route('/question_replies/')
@app.route('/question_replies/<int:page>/')
def question_replies(page=0):
    """
    Page through all available question_replies.
    """

    logger.debug("question_replies page called")
    committee_list = load_from_api('committee', return_everything=True)
    committees = committee_list['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    question_replies_list = load_from_api(
        'question_reply',
        page=page,
        params=params)
    count = question_replies_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    question_replies = question_replies_list['results']
    url = "/question_replies"
    return render_template(
        'list.html',
        results=question_replies,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="question-circle",
        title="Questions and Replies",
        content_type="question_reply",
        committees=committees,
        filters=filters)


@app.route('/search/')
@app.route('/search/<int:page>/')
def search(page=0):
    """
    Display search page
    """
    filters = {}
    filters["type"] = request.args.get('filter[type]', '')
    filters["start_date"] = request.args.get('filter[start_date]', '')
    filters["end_date"] = request.args.get('filter[end_date]', '')
    filters["committee"] = request.args.get('filter[committee]', '')

    # support legacy search URLs that allowed "None" as a value
    for k, v in filters.iteritems():
        if v == "None":
            filters[k] = None

    q = request.args.get('q', '').strip()

    params = dict(filters)
    params["q"] = q
    params["page"] = page

    # do the search
    search = load_from_api('search', params=params)

    years = range(1997, datetime.now().year + 1)
    years.reverse()

    bincount = {}
    for bin in search["bincount"]["types"]:
        bincount[bin["key"]] = bin["doc_count"]
    yearcount = {}
    for year in search["bincount"]["years"]:
        yearcount[int(year["key_as_string"][:4])] = year["doc_count"]

    committees = load_from_api('committee', return_everything=True)['results']

    search_types = [
            ("committee", "Committees"),
            ("committee_meeting", "Committee Meetings"),
            ("bill", "Bills"),
            ("member", "MPs"),
            ("hansard", "Hansards"),
            ("briefing", "Media Briefings"),
            ("question_reply", "Question & Reply"),
            ("tabled_committee_report", "Tabled Committee Reports"),
            ("call_for_comment", "Calls for Comments"),
            ("policy_document", "Policy Documents"),
            ("gazette", "Gazettes"),
            ("daily_schedule", "Daily Schedules"),
            ]

    def search_url(**kwargs):
        args = dict(filters)
        args.update(kwargs)
        args = {('filter[%s]' % k): v for k, v in args.iteritems() if v}
        return url_for('search', q=q, **args)

    return render_template(
        'search.html',
        q=q,
        search=search,
        num_pages=search["pages"],
        page=search["page"],
        per_page=search["per_page"],
        search_url=search_url,
        url=url_for('search')[:-1],
        query_string=request.query_string,
        filters=filters,
        years=years,
        bincount=bincount,
        yearcount=yearcount,
        committees=committees,
        search_types=search_types)

@app.route('/page/<path:pagename>')
def page(pagename):
    """
    Serves a page from templates/pages
    """
    logger.debug("Attempting to serve page: " + pagename)
    page = load_from_api('page', params={'slug': pagename})

    if page['slug'] != pagename:
        return redirect(url_for('page', pagename=page['slug']))

    return render_template('page.html',
        page=page,
        admin_edit_url=admin_url('pages', page['id']))


# some old content contains links files which are in S3:
#   /docs/foo
#   /questions/foo
#   /mp3/foo
#   /files/foo
#   /files/doc/foo
#   /files/docs/foo
@app.route('/<any(docs, mp3, questions):dir>/<path:path>')
@app.route('/files/<path:path>')
def docs(path, dir=''):
    if dir:
        dir = dir + '/'
    return redirect(app.config['STATIC_HOST'] + dir + path)
