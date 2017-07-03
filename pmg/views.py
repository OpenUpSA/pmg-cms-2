import logging
from datetime import datetime, date, timedelta
import math
from urlparse import urlparse, urlunparse
from bs4 import BeautifulSoup
from sqlalchemy import desc, Float
from sqlalchemy.sql.expression import case, func, cast

from flask import request, flash, url_for, session, render_template, abort, redirect
from flask.ext.security import current_user
from flask.ext.mail import Message
from flask import make_response

from pmg import app, mail
from pmg.bills import bill_history, MIN_YEAR
from pmg.api.client import load_from_api, ApiException
from pmg.search import Search
from pmg.models import Redirect, Page, SavedSearch, Featured, CommitteeMeeting, CommitteeMeetingAttendance, db
from pmg.models.resources import Committee

from copy import deepcopy
from collections import OrderedDict

import forms
import utils
from helpers import _jinja2_filter_datetime as pretty_date

import json

LEGACY_DOMAINS = set(['new.pmg.org.za', 'www.pmg.org.za', 'bills.pmg.org.za', 'www.legacy.pmg.org.za', 'legacy.pmg.org.za'])

app.session = session

logger = logging.getLogger(__name__)


def admin_url(model_name, id):
    return '/admin/%s/edit/?id=%s' % (model_name, id)


@app.errorhandler(404)
def page_not_found(error):
    dest = Redirect.for_url(request.path)
    if dest:
        return redirect(dest, code=302)

    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html', error=error), 500


@app.before_request
def shortcircuit_wget():
    """
    Respond immediately with a message that would typically be shown in Wget
    crawling output because crawling the site is expensive to us and we'd prefer
    they get in touch first.
    """
    if "Wget" in request.headers.get('user-agent', ''):
        resp = make_response("""
        Hi!

        It looks like you're crawling us. We'd love to get in touch and see if
        there's a better way we can share this content with you.

        Send us a mail at info@code4sa.org

        Best
        Code4SA (The pmg.org.za developers)
        """)
        logger.info("Saying hi to crawler.")
        return resp, "418 Hi, email us at info@code4sa.org"


@app.before_request
def redirect_legacy_domains():
    """ Redirect legacy domains to the primary domain. """
    parts = urlparse(request.url)
    if parts.netloc in LEGACY_DOMAINS:
        parts = list(parts)
        parts[1] = app.config['SERVER_NAME']
        return redirect(urlunparse(parts), code=301)


@app.before_request
def update_last_login():
    if current_user.is_authenticated():
        # keep track of the last visit
        current_user.update_current_login()


def classify_attachments(files):
    """ Return an (audio_files, related_docs) tuple. """
    audio = []
    related = []

    for f in files:
        if 'audio' in f['file_mime']:
            audio.append(f)
        else:
            related.append(f)

    return audio, related


def get_featured_content():
    info = {}

    info['feature'] = Featured.query.order_by(desc(Featured.start_date)).first()
    info['committee_meetings'] = CommitteeMeeting.query\
        .filter(CommitteeMeeting.featured == True)\
        .order_by(desc(CommitteeMeeting.date))\
        .limit(12)\
        .all()  # noqa

    info['pages'] = Page.query\
        .filter(Page.featured == True)\
        .order_by(desc(Page.updated_at))\
        .limit(12)\
        .all()  # noqa

    for page in info['pages']:
        page.type = 'page'

        # use the first sentence as an excerpt for the page
        soup = BeautifulSoup(page.body, "html.parser")
        for idx, p in enumerate(soup.findAll('p')):
            if idx == 0 and (p.findAll('strong')
                             or p.findAll('h1')
                             or p.findAll('h2')):
                # Skip first para if it contains strong - probably a heading
                continue
            p_texts = p.findAll(text=True)
            if p_texts:
                page.first_para = p_texts[0]
                break

    # choose most recent 12 pages and meetings
    info['content'] = info['committee_meetings'] + info['pages']
    info['content'] = sorted(info['content'], key=lambda x: getattr(x, 'date', getattr(x, 'updated_at')), reverse=True)[:12]

    return info


@app.context_processor
def inject_via():
    # inject the 'via' query param into the page (easier than parsing the querystring in JS)
    # so that we can track it with GA
    if request.args.get('via'):
        return {'via_tag': request.args.get('via').strip()}
    return {'via_tag': None}


@app.route('/')
def index():
    committee_meetings = load_from_api('v2/committee-meetings', fields=['id', 'date', 'title', 'committee.name'], params={'per_page': 11})['results']
    bills = load_from_api('bill/current', return_everything=True)["results"]
    bills.sort(key=lambda b: b['updated_at'], reverse=True)
    questions = load_from_api('v2/minister-questions', fields=['id', 'question_to_name', 'question', 'date'], params={'per_page': 11})['results']

    return render_template(
        'index.html',
        committee_meetings=committee_meetings,
        bills=bills[:11],
        questions=questions,
        stock_pic="sa-parliament.jpg",
        featured_content=get_featured_content(),
    )


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
        year_list = range(MIN_YEAR, date.today().year + 1)
        year_list.reverse()
        params = {}

        if not year:
            return redirect(url_for('bills', bill_type=bill_type, year=year_list[0]))

        if year not in year_list:
            abort(404)
        params = 'filter[year]=%d' % year

    api_url = 'bill' if bill_type == 'all' else 'bill/%s' % bill_type
    bills = load_from_api(api_url, return_everything=True, params=params)['results']

    bills.sort(key=lambda b: [-b['year'], b['type']['prefix'], b.get('number', 0), b['title']])

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
    stages = {
        'enacted': '5',
        'president': '4',
        'ncop': '3',
        'returned-to-na': '3',
        'na': '2',
        'introduced': 1,
    }
    history = bill_history(bill)

    if 'status' in bill:
        social_summary = bill['code'] + ", introduced " + pretty_date(bill['date_of_introduction'], 'long') + ". " + bill['status']['description']
    else:
        social_summary = bill['code'] + ", introduced " + pretty_date(bill['date_of_introduction'], 'long')
    return render_template('bills/detail.html',
        bill=bill,
        history=history,
        stages=stages,
        social_summary=social_summary,
        admin_edit_url=admin_url('bill', bill_id))


@app.route('/committee/<int:committee_id>')
@app.route('/committee/<int:committee_id>/')
def committee_detail(committee_id):
    """
    Display all available detail for the committee.
    """
    committee = load_from_api('v2/committees', committee_id)['result']
    filtered_meetings = {}

    # calls for comment
    committee['calls_for_comments'] = load_from_api(
        'v2/committees/%s/calls-for-comment' % committee_id,
        fields=['id', 'title', 'start_date'],
        return_everything=True)['results']

    # tabled reports
    committee['tabled_committee_reports'] = load_from_api(
        'v2/committees/%s/tabled-reports' % committee_id,
        fields=['id', 'title', 'start_date'],
        return_everything=True)['results']

    # memberships
    membership = load_from_api(
        'v2/committees/%s/members' % committee_id,
        return_everything=True)['results']
    sorter = lambda x: x['member']['name']
    membership = sorted([m for m in membership if m['chairperson']], key=sorter) + \
                 sorted([m for m in membership if not m['chairperson']], key=sorter)

    # attendance
    subquery = db.session.query(
        func.date_part('year', CommitteeMeeting.date).label('year'),
        func.count(case([(CommitteeMeetingAttendance.attendance.in_(CommitteeMeetingAttendance.ATTENDANCE_CODES_PRESENT), 1)])).label('n_present'),
        func.count(CommitteeMeetingAttendance.id).label('n_members')
        )\
        .group_by('year', CommitteeMeeting.id)\
        .filter(CommitteeMeeting.committee_id == committee_id)\
        .filter(CommitteeMeetingAttendance.meeting_id == CommitteeMeeting.id)\
        .subquery('attendance')

    attendance_summary = db.session.query(
        subquery.c.year,
        func.count(1).label('n_meetings'),
        func.avg(cast(subquery.c.n_present, Float) / subquery.c.n_members).label('avg_attendance'),
        cast(func.avg(subquery.c.n_members), Float).label('avg_members')
        )\
        .group_by(subquery.c.year)\
        .order_by(subquery.c.year)\
        .all()

    recent_questions = load_from_api('minister-questions-combined', params={'filter[committee_id]': committee_id})['results']

    # meetings
    all_meetings = load_from_api('v2/committees/%s/meetings' % committee_id,
                                 fields=['id', 'title', 'date'], return_everything=True)['results']

    for meeting in all_meetings:
        d = meeting['parsed_date'] = datetime.strptime(meeting['date'][:10], "%Y-%m-%d")
        if d.year not in filtered_meetings:
            filtered_meetings[d.year] = []
        filtered_meetings[d.year].append(meeting)

    latest_year = max(y for y in filtered_meetings) if filtered_meetings else None
    earliest_year = min(y for y in filtered_meetings) if filtered_meetings else None
    now = datetime.now()
    six_months = timedelta(days=30 * 6)  # 6 months
    filtered_meetings['six-months'] = [m for m in all_meetings if (now - m['parsed_date']) <= six_months]

    if filtered_meetings['six-months']:
        starting_filter = 'six-months'
    else:
        starting_filter = latest_year

    social_summary = "Meetings, calls for comment, reports, and questions and replies of the " + committee['name'] + " committee."

    return render_template('committee_detail.html',
                           current_year=now.year,
                           earliest_year=earliest_year,
                           filtered_meetings=filtered_meetings,
                           committee=committee,
                           membership=membership,
                           has_meetings=len(all_meetings) > 0,
                           starting_filter=starting_filter,
                           recent_questions=recent_questions,
                           social_summary=social_summary,
                           attendance_summary=attendance_summary,
                           admin_edit_url=admin_url('committee', committee_id))


@app.route('/attendance-overview')
def attendance_overview():
    """
    Display overview of attendance for meetings.
    """

    # attendance
    subquery = db.session.query(
        Committee.name.label('committee_name'),
        Committee.id.label('committee_id'),
        func.date_part('year', CommitteeMeeting.date).label('year'),
        func.count(case([(CommitteeMeetingAttendance.attendance.in_(
            CommitteeMeetingAttendance.ATTENDANCE_CODES_PRESENT
        ), 1)])).label('n_present'),
        func.count(CommitteeMeetingAttendance.id).label('n_members')
    )\
                         .group_by('year', CommitteeMeeting.id, Committee.name, Committee.id)\
                         .filter(CommitteeMeetingAttendance.meeting_id == CommitteeMeeting.id)\
                         .filter(Committee.ad_hoc == False)\
                         .subquery('attendance')

    attendance_overview = [
        (u'Monitoring Improvement of Quality of Life and Status of Women', 100, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Standing Committee on Auditor General', 50, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Trade and Industry', 98, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'International Relations', 49, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Appropriations', 56, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Committe on Delegated Legislation', 6, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Economic Development', 2, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Monitoring Committee on Children, Youth and Persons with Disabilities', 78, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Rules of the National Assembly', 68, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Cooperative Governance and Traditional Affairs', 65, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Finance', 75, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Economic and Business Development', 97, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Public Accounts', 42, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Finance Standing Committee', 24, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Trade and International Relations', 69, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Committee on the Executive Members Ethics Bill', 66, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Defence and Military Veterans', 87, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Standing Committee on Appropriations', 61, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Budget Committee on Appropriation', 15, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Mineral Resources', 58, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Environmental Affairs', 108, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Transport', 26, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Labour', 62, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Land and Mineral Resources', 20, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Water and Sanitation', 111, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Constitutional Review Committee', 52, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Standing Committee on Financial Management of Parliament', 130, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Justice and Correctional Services', 38, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Health', 63, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Rural Development and Land Reform', 95, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Security and Justice', 67, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Petitions and Executive Undertakings', 88, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Agriculture, Forestry and Fisheries', 37, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Women in The Presidency', 51, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Public Enterprises', 73, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u"Ethics and Members' Interest", 77, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Energy', 3, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Social Services', 60, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Committee of Chairpersons', 8, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Communications and Public Enterprise', 10, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Home Affairs', 110, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Tourism', 9, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Sport and Recreation', 94, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Public Service and Administration, Performance Monitoring and Evaluation', 71, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Committee on HIV and AIDS', 34, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Rules', 33, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Correctional Services', 40, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Police', 86, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Women, Children and People with Disabilities', 43, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Science and Technology', 23, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u"Private Members' Legislative Proposals and Special Petitions", 112, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Public Services', 31, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Education and Recreation', 11, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Communications', 103, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Defence', 85, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Basic Education', 28, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Small Business Development', 116, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Cooperative Governance & Traditional Affairs', 83, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Social Development', 19, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Human Settlements', 91, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Higher Education and Training', 64, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Telecommunications and Postal Services', 117, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Public Works', 32, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'NCOP Rules of the National Council of Provinces', 101, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Arts and Culture', 106, 2014.0, 647L, 0.707117697154526, 11.4250386398764),
        (u'Joint Rules', 33, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Women in The Presidency', 51, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Agriculture, Forestry and Fisheries', 37, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Land and Mineral Resources', 20, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Tourism', 9, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Sport and Recreation', 94, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Public Service and Administration, Performance Monitoring and Evaluation', 71, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Rules of the National Council of Provinces', 101, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Joint Committee on HIV and AIDS', 34, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Economic Development', 2, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Education and Recreation', 11, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Women, Children and People with Disabilities', 43, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Standing Committee on Auditor General', 50, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Trade and Industry', 98, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Joint Committe on Delegated Legislation', 6, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Public Accounts', 42, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Water and Sanitation', 111, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Home Affairs', 110, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u"Ethics and Members' Interest", 77, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Higher Education and Training', 64, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Trade and International Relations', 69, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Public Works', 32, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Finance Standing Committee', 24, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Arts and Culture', 106, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Cooperative Governance & Traditional Affairs', 83, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Small Business Development', 116, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Joint Monitoring Committee on Children, Youth and Persons with Disabilities', 78, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Monitoring Improvement of Quality of Life and Status of Women', 100, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Cooperative Governance and Traditional Affairs', 65, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Social Services', 60, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Energy', 3, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Public Enterprises', 73, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Economic and Business Development', 97, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Basic Education', 28, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Human Settlements', 91, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Committee of Chairpersons', 8, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'International Relations', 49, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Rules of the National Assembly', 68, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Finance', 75, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Rural Development and Land Reform', 95, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Health', 63, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Social Development', 19, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Standing Committee on Appropriations', 61, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Transport', 26, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Telecommunications and Postal Services', 117, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Petitions and Executive Undertakings', 88, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Joint Standing Committee on Financial Management of Parliament', 130, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Mineral Resources', 58, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Budget Committee on Appropriation', 15, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Environmental Affairs', 108, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Joint Committee on the Executive Members Ethics Bill', 66, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u"Private Members' Legislative Proposals and Special Petitions", 112, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Justice and Correctional Services', 38, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Communications', 103, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Defence', 85, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Public Services', 31, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Labour', 62, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Police', 86, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Defence and Military Veterans', 87, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Correctional Services', 40, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Constitutional Review Committee', 52, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'Science and Technology', 23, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Communications and Public Enterprise', 10, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Security and Justice', 67, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Appropriations', 56, 2015.0, 1149L, 0.632853522440305, 12.7563098346388),
        (u'NCOP Trade and International Relations', 69, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Rural Development and Land Reform', 95, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Transport', 26, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Health', 63, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Social Services', 60, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Public Enterprises', 73, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Correctional Services', 40, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Police', 86, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Defence', 85, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Communications', 103, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Public Services', 31, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Communications and Public Enterprise', 10, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Budget Committee on Appropriation', 15, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Standing Committee on Financial Management of Parliament', 130, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Petitions and Executive Undertakings', 88, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Justice and Correctional Services', 38, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Defence and Military Veterans', 87, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Environmental Affairs', 108, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Mineral Resources', 58, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Appropriations', 56, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Economic and Business Development', 97, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Finance', 75, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Finance Standing Committee', 24, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Trade and Industry', 98, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Standing Committee on Auditor General', 50, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Arts and Culture', 106, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Small Business Development', 116, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Cooperative Governance & Traditional Affairs', 83, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Public Service and Administration, Performance Monitoring and Evaluation', 71, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Rules', 33, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Human Settlements', 91, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'International Relations', 49, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Monitoring Committee on Children, Youth and Persons with Disabilities', 78, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Monitoring Improvement of Quality of Life and Status of Women', 100, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Cooperative Governance and Traditional Affairs', 65, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Energy', 3, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u"Private Members' Legislative Proposals and Special Petitions", 112, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Committee on the Executive Members Ethics Bill', 66, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Constitutional Review Committee', 52, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Science and Technology', 23, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Social Development', 19, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Telecommunications and Postal Services', 117, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Basic Education', 28, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Committee of Chairpersons', 8, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Land and Mineral Resources', 20, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Standing Committee on Appropriations', 61, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Rules of the National Assembly', 68, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Labour', 62, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Education and Recreation', 11, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Committee on HIV and AIDS', 34, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Water and Sanitation', 111, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Public Accounts', 42, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Joint Committe on Delegated Legislation', 6, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Security and Justice', 67, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Rules of the National Council of Provinces', 101, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Tourism', 9, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Sport and Recreation', 94, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Agriculture, Forestry and Fisheries', 37, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Women in The Presidency', 51, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u"Ethics and Members' Interest", 77, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Home Affairs', 110, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Higher Education and Training', 64, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'NCOP Women, Children and People with Disabilities', 43, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Economic Development', 2, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Public Works', 32, 2016.0, 1154L, 0.647064826376044, 13.0381282495667),
        (u'Economic Development', 2, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Women, Children and People with Disabilities', 43, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Social Development', 19, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Home Affairs', 110, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u"Ethics and Members' Interest", 77, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Higher Education and Training', 64, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Telecommunications and Postal Services', 117, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Rules of the National Council of Provinces', 101, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Committee on the Executive Members Ethics Bill', 66, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Mineral Resources', 58, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Energy', 3, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Environmental Affairs', 108, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Sport and Recreation', 94, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u"Private Members' Legislative Proposals and Special Petitions", 112, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Tourism', 9, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Defence and Military Veterans', 87, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Agriculture, Forestry and Fisheries', 37, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Finance Standing Committee', 24, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Women in The Presidency', 51, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Security and Justice', 67, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Economic and Business Development', 97, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Finance', 75, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Water and Sanitation', 111, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Human Settlements', 91, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Public Accounts', 42, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Committe on Delegated Legislation', 6, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Appropriations', 56, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Education and Recreation', 11, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Rules', 33, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Constitutional Review Committee', 52, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'International Relations', 49, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Standing Committee on Auditor General', 50, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Trade and Industry', 98, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Arts and Culture', 106, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Committee on HIV and AIDS', 34, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Rules of the National Assembly', 68, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Standing Committee on Appropriations', 61, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Labour', 62, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Public Service and Administration, Performance Monitoring and Evaluation', 71, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Land and Mineral Resources', 20, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Science and Technology', 23, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Monitoring Committee on Children, Youth and Persons with Disabilities', 78, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Monitoring Improvement of Quality of Life and Status of Women', 100, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Cooperative Governance & Traditional Affairs', 83, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Correctional Services', 40, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Police', 86, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Communications and Public Enterprise', 10, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Small Business Development', 116, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Public Services', 31, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Petitions and Executive Undertakings', 88, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Joint Standing Committee on Financial Management of Parliament', 130, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Budget Committee on Appropriation', 15, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Defence', 85, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Communications', 103, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Public Enterprises', 73, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Basic Education', 28, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Social Services', 60, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Committee of Chairpersons', 8, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Cooperative Governance and Traditional Affairs', 65, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Transport', 26, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Justice and Correctional Services', 38, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Health', 63, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Rural Development and Land Reform', 95, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'NCOP Trade and International Relations', 69, 2017.0, 689L, 0.619810035471253, 13.6240928882438),
        (u'Public Works', 32, 2017.0, 689L, 0.619810035471253, 13.6240928882438)
    ]

    return render_template('attendance_overview.html',
                           attendance_overview_json=json.dumps(attendance_overview),
                           attendance_overview=attendance_overview,
    )


@app.route('/committee-question/<int:question_id>/')
def committee_question(question_id):
    """ Display a single committee question.
    """
    question = load_from_api('committee-question', question_id)
    committee = question['committee']
    social_summary = "A question to the " + question['question_to_name'] + ", asked on " + pretty_date(question['date'], 'long') + " by " + question['asked_by_name']

    return render_template('committee_question.html',
                           committee=committee,
                           question=question,
                           hide_replies=False,
                           content_date=question['date'],
                           social_summary=social_summary,
                           admin_edit_url=admin_url('committee-question', question_id))


@app.route('/committees/')
def committees():
    """
    Page through all available committees.
    """
    committees = load_from_api('v2/committees', return_everything=True, fields=['id', 'name', 'premium', 'ad_hoc', 'active', 'house'])['results']

    nat = {
        'name': 'National Assembly',
        'committees': []
    }
    ncp = {
        'name': 'National Council of Provinces',
        'committees': []
    }
    jnt = {
        'name': 'Joint Committees',
        'committees': []
    }

    adhoc_committees = OrderedDict((('nat', nat), ('ncp', ncp), ('jnt', jnt)))

    reg_committees = deepcopy(adhoc_committees)
    committees_type = None

    for committee in committees:
        if committee['ad_hoc'] is True:
            committees_type = adhoc_committees
        else:
            committees_type = reg_committees

        if current_user.is_authenticated():
            user_following = current_user.following

            # Check if user is following committee
            if current_user.is_authenticated() and committee['id'] in [ufc.id for ufc in user_following]:
                committee['followed'] = True

        if committee['house']:
            if committee['house']['id'] is Committee.NATIONAL_ASSEMBLY:
                committees_type['nat']['committees'].append(committee)
            elif committee['house']['id'] is Committee.NAT_COUNCIL_OF_PROV:
                committees_type['ncp']['committees'].append(committee)
            elif committee['house']['id'] is Committee.JOINT_COMMITTEE:
                committees_type['jnt']['committees'].append(committee)

    for typ in adhoc_committees.itervalues():
        typ['committees'].sort(key=lambda x: (not x['active'], x['name']))

    return render_template(
        'committee_list.html',
        reg_committees=reg_committees,
        adhoc_committees=adhoc_committees
    )


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

    event = load_from_api('v2/committee-meetings', event_id)['result']

    if event.get('premium_content_excluded'):
        premium_committees = load_from_api('committee/premium', return_everything=True)['results']
    else:
        premium_committees = None

    audio, related_docs = classify_attachments(event.get('files', []))

    attendance = load_from_api(
        'v2/committee-meetings/%s/attendance' % event_id,
        return_everything=True)['results']
    attendance = [a for a in attendance if a['attendance'] in CommitteeMeetingAttendance.ATTENDANCE_CODES_PRESENT]
    sorter = lambda x: x['member']['name']
    attendance = sorted([a for a in attendance if a['chairperson']], key=sorter) + \
                 sorted([a for a in attendance if not a['chairperson']], key=sorter)
    if event['chairperson']:
        social_summary="A meeting of the " + event['committee']['name'] + " committee held on " + pretty_date(event['date'], 'long') + ", lead by " + event['chairperson']
    else:
        social_summary="A meeting of the " + event['committee']['name'] + " committee held on " + pretty_date(event['date'], 'long') + "."

    return render_template(
        'committee_meeting.html',
        event=event,
        committee=event['committee'],
        audio=audio,
        related_docs=related_docs,
        attendance=attendance,
        premium_committees=premium_committees,
        content_date=event['date'],
        social_summary=social_summary,
        admin_edit_url=admin_url('committee-meeting', event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config['SOUNDCLOUD_APP_KEY_ID']),


@app.route('/tabled-committee-reports/')
@app.route('/tabled-committee-reports/<int:page>/')
def tabled_committee_reports(page=0):
    """
    Page through all available tabled-committee-reports.
    """

    logger.debug("tabled-committee-reports page called")
    committees = load_from_api('committee', return_everything=True)['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    tabled_committee_reports_list = load_from_api(
        'tabled-committee-report',
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
        'tabled-committee-report',
        tabled_committee_report_id)
    logger.debug(tabled_committee_report)
    return render_template(
        'tabled_committee_report_detail.html',
        tabled_committee_report=tabled_committee_report,
        content_date=tabled_committee_report['start_date'],
        admin_edit_url=admin_url('tabled-committee-report', tabled_committee_report_id))


@app.route('/calls-for-comments/')
@app.route('/calls-for-comments/<int:page>/')
def calls_for_comments(page=0):
    """
    Page through all available calls-for-comments.
    """

    logger.debug("calls-for-comments page called")
    committees = load_from_api('committee', return_everything=True)['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    call_for_comment_list = load_from_api(
        'v2/calls-for-comments',
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
        'v2/calls-for-comments',
        call_for_comment_id)['result']
    logger.debug(call_for_comment)

    if call_for_comment['committee']:
        cfc_committee = 'A call for comments by the ' + call_for_comment['committee']['name'] + " committee. "
    else:
        cfc_committee = 'A call for comments. '
    if call_for_comment['end_date']:
        cfc_deadline = 'Submissions must be received by no later than ' + pretty_date(call_for_comment['end_date'], 'long')
        if call_for_comment['closed']:
            cfc_deadline = 'Submissions closed ' + pretty_date(call_for_comment['end_date'], 'long')
    else:
        cfc_deadline = ''

    social_summary = cfc_committee + cfc_deadline

    return render_template(
        'call_for_comment_detail.html',
        call_for_comment=call_for_comment,
        content_date=call_for_comment['start_date'],
        social_summary=social_summary,
        admin_edit_url=admin_url('call-for-comment', call_for_comment_id))


@app.route('/policy-documents/')
@app.route('/policy-documents/<int:page>/')
def policy_documents(page=0):
    """
    Page through all available policy-documents.
    """

    logger.debug("policy-documents page called")
    policy_documents_list = load_from_api('policy-document', page=page)
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
    policy_document = load_from_api('policy-document', policy_document_id)
    logger.debug(policy_document)
    return render_template(
        'policy_document_detail.html',
        policy_document=policy_document,
        content_date=policy_document['start_date'],
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
        content_date=gazette['start_date'],
        admin_edit_url=admin_url('gazette', gazette_id))


@app.route('/members/')
def members():
    """ All MPs.
    """
    members = load_from_api('v2/members', return_everything=True)['results']

    # partition by house
    members_by_house = {}
    for member in members:
        if member.get('house') and member['current']:
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
    audio, related_docs = classify_attachments(event.get('files', []))

    return render_template(
        'hansard_detail.html',
        event=event,
        audio=audio,
        related_docs=related_docs,
        content_date=event['date'],
        admin_edit_url=admin_url('hansard', event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config['SOUNDCLOUD_APP_KEY_ID'])


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
    audio, related_docs = classify_attachments(event.get('files', []))

    return render_template(
        'briefing_detail.html',
        event=event,
        audio=audio,
        related_docs=related_docs,
        content_date=event['date'],
        admin_edit_url=admin_url('briefing', event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config['SOUNDCLOUD_APP_KEY_ID'])


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
    daily_schedule = load_from_api('daily-schedule', daily_schedule_id)
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
    daily_schedules_list = load_from_api('daily-schedule', page=page)
    count = daily_schedules_list["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))
    daily_schedules = daily_schedules_list['results']
    url = "/daily-schedules"
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
    question_reply = load_from_api('question_reply', question_reply_id)

    if question_reply.get('committee'):
        template = 'committee_question_reply.html'
    else:
        template = 'question_reply_detail.html'

    return render_template(
        template,
        question_reply=question_reply,
        committee=question_reply.get('committee'),
        content_date=question_reply['start_date'],
        admin_edit_url=admin_url('question', question_reply_id))


@app.route('/question_replies/')
@app.route('/question_replies/<int:page>/')
def question_replies(page=0):
    """
    Page through all available question_replies + committee_questions.
    """
    logger.debug("question_replies page called")
    committees = load_from_api('committee/question_reply', return_everything=True)['results']
    filters = {}
    params = {}
    filters["committee"] = params[
        'filter[committee_id]'] = request.args.get('filter[committee]')
    questions = load_from_api(
        'minister-questions-combined',
        page=page,
        params=params)
    count = questions["count"]
    per_page = app.config['RESULTS_PER_PAGE']
    num_pages = int(math.ceil(float(count) / float(per_page)))

    url = "/question_replies"

    return render_template(
        'question_list.html',
        questions=questions,
        hide_replies=True,
        url=url,
        num_pages=num_pages,
        per_page=per_page,
        page=page,
        icon="question-circle",
        title="Questions and Replies",
        content_type="minister_question",
        committees=committees,
        all_committees_option="All Ministries",
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
    search = {}
    try:
        if q:
            search = load_from_api('search', params=params)
    except ApiException as e:
        if e.code == 422:
            # bad search, eg: "   "
            q = ""
        else:
            raise e

    years = range(1997, datetime.now().year + 1)
    years.reverse()

    bincount = {}
    yearcount = {}
    if search:
        for bin in search["bincount"]["types"]:
            bincount[bin["key"]] = bin["doc_count"]

        for year in search["bincount"]["years"]:
            yearcount[int(year["key_as_string"][:4])] = year["doc_count"]

        search['friendly_data_type'] = Search.friendly_data_types.get(filters['type'], None)

    committees = load_from_api('committee', return_everything=True)['results']

    def search_url(**kwargs):
        args = dict(filters)
        args.update(kwargs)
        args = {('filter[%s]' % k): v for k, v in args.iteritems() if v}
        return url_for('search', q=q, **args)

    saved_search = None
    if not current_user.is_anonymous():
        saved_search = SavedSearch.find(
            current_user,
            q,
            content_type=filters['type'] or None,
            committee_id=filters['committee'] or None)

    if filters['committee']:
        for committee in committees:
            if committee['id'] == int(filters['committee']):
                search['filtered_committee_name'] = committee['name']
                break

    # suggest a phrase search?
    if q and ' ' in q and '"' not in q:
        suggest_phrase = '"%s"' % q
        kwargs = {('filter[%s]' % k): v for k, v in filters.iteritems() if v}
        kwargs['q'] = suggest_phrase
        suggest_phrase_url = url_for('search', **kwargs)
    else:
        suggest_phrase = False
        suggest_phrase_url = None

    return render_template(
        'search.html',
        q=q,
        search=search,
        num_pages=search.get("pages"),
        page=search.get("page"),
        per_page=search.get("per_page"),
        search_url=search_url,
        url=url_for('search')[:-1],
        query_string=request.query_string,
        filters=filters,
        years=years,
        bincount=bincount,
        yearcount=yearcount,
        committees=committees,
        search_types=Search.friendly_data_types.items(),
        saved_search=saved_search,
        suggest_phrase=suggest_phrase,
        suggest_phrase_url=suggest_phrase_url)


@app.route('/page/<path:pagename>')
def page(pagename):
    """
    Serves a page from templates/pages
    """
    logger.debug("Attempting to serve page: " + pagename)

    pagename = Page().validate_slug(None, pagename)
    page = Page.query.filter(Page.slug == pagename).first()
    if not page:
        abort(404)

    files = [f.file for f in (page.files or [])]
    files.sort(key=lambda f: (f.title, f.file_path))

    return render_template('page.html',
                           page=page,
                           attachments=files,
                           admin_edit_url=admin_url('pages', page.id))


# Redirect to content stored in S3.
#
# For current content, we always have URLs like /files/the/file.pdf
# which must be redirected to S3/the/file.pdf.
#
# Legacy content from the old website can be under a few other paths, too.
#   /docs/foo
#   /questions/foo
#   /mp3/foo
@app.route('/<any(docs, mp3, questions):dir>/<path:path>')
@app.route('/files/<path:path>')
def docs(path, dir=''):
    if dir:
        dir = dir + '/'

    # report to google analytics
    try:
        utils.track_pageview()
    except StandardError as e:
        logger.error("Error tracking pageview: %s" % e.message, exc_info=e)

    return redirect(app.config['STATIC_HOST'] + dir + path)


@app.route('/correct-this-page', methods=['POST'])
def correct_this_page():
    form = forms.CorrectThisPageForm(request.form)
    if form.validate_on_submit():
        msg = Message("Correct This Page feedback", recipients=["correct@pmg.org.za"], sender='info@pmg.org.za')
        msg.html = render_template('correct_this_page.html', submission={
            'url': form.url.data,
            'details': form.details.data,
            'email': form.email.data,
        })
        mail.send(msg)

        flash('Thanks for your feedback.', 'info')

    return redirect(request.form.get('url', '/'))
