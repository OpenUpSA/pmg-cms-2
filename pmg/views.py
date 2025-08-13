import os
from builtins import range
import logging
from datetime import datetime, date, timedelta
import math
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from sqlalchemy import desc, func, cast, Integer, text
from itertools import groupby
from unidecode import unidecode
import requests

from flask import (
    request,
    flash,
    url_for,
    session,
    render_template,
    abort,
    redirect,
    Response,
    jsonify,
    send_from_directory,
)
from flask_security import current_user
from flask_mail import Message
from flask import make_response
from slugify import slugify

from pmg import app, db, mail, cache, cache_key, should_skip_cache
from pmg.bills import bill_history, MIN_YEAR
from pmg.api.client import load_from_api, ApiException
from pmg.api.v1 import create_next_page_url
from pmg.search import Search
from pmg.models import (
    Redirect,
    Page,
    Post,
    SavedSearch,
    Featured,
    CommitteeMeeting,
    CommitteeMeetingAttendance,
    House,
    Petition
)
from pmg.models.resources import Committee

from copy import deepcopy
from collections import OrderedDict

from . import forms
from . import utils
from .helpers import _jinja2_filter_datetime as pretty_date
from .user_management import follow_committee


LEGACY_DOMAINS = set(
    [
        "new.pmg.org.za",
        "www.pmg.org.za",
        "bills.pmg.org.za",
        "www.legacy.pmg.org.za",
        "legacy.pmg.org.za",
    ]
)

app.session = session

logger = logging.getLogger(__name__)


def admin_url(model_name, id):
    return "/admin/%s/edit/?id=%s" % (model_name, id)


@app.errorhandler(404)
def page_not_found(error):
    dest = Redirect.for_url(request.path)
    if dest:
        return redirect(dest, code=302)

    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html", error=error), 500


@app.before_request
def shortcircuit_wget():
    """
    Respond immediately with a message that would typically be shown in Wget
    crawling output because crawling the site is expensive to us and we'd prefer
    they get in touch first.
    """
    if "Wget" in request.headers.get("user-agent", ""):
        resp = make_response(
            """
        Hi!

        It looks like you're crawling us. We'd love to get in touch and see if
        there's a better way we can share this content with you.

        Send us a mail at info@openup.org.za

        Best
        OpenUp (The pmg.org.za developers)
        """
        )
        logger.info("Saying hi to crawler.")
        return resp, "418 Hi, email us at info@openup.org.za"


@app.before_request
def redirect_legacy_domains():
    """Redirect legacy domains to the primary domain."""
    parts = urlparse(request.url)
    if parts.netloc in LEGACY_DOMAINS:
        parts = list(parts)
        parts[1] = app.config["SERVER_NAME"]
        return redirect(urlunparse(parts), code=301)


@app.before_request
def update_last_login():
    if current_user.is_authenticated:
        # keep track of the last visit
        current_user.update_current_login()


def classify_attachments(files):
    """Return an (audio_files, related_docs) tuple."""
    audio = []
    related = []

    for f in files:
        if "audio" in f["file_mime"]:
            audio.append(f)
        else:
            related.append(f)

    return audio, related


@cache.cached(timeout=10800, key_prefix="get_featured_content")
def get_featured_content():
    info = {}

    info["features"] = Featured.query.order_by(desc(Featured.start_date)).all()
    info["committee_meetings"] = (
        CommitteeMeeting.query.filter(CommitteeMeeting.featured == True)
        .order_by(desc(CommitteeMeeting.date))
        .limit(12)
        .all()
    )  # noqa

    info["pages"] = (
        Page.query.filter(Page.featured == True)
        .order_by(desc(Page.updated_at))
        .limit(12)
        .all()
    )  # noqa

    for page in info["pages"]:
        page.type = "page"

        # use the first sentence as an excerpt for the page
        soup = BeautifulSoup(page.body, "html.parser")
        for idx, p in enumerate(soup.findAll("p")):
            if idx == 0 and (p.findAll("strong") or p.findAll("h1") or p.findAll("h2")):
                # Skip first para if it contains strong - probably a heading
                continue
            p_texts = p.findAll(text=True)
            if p_texts:
                page.first_para = p_texts[0]
                break

    # choose most recent 12 pages and meetings
    info["content"] = info["committee_meetings"] + info["pages"]
    info["content"] = sorted(
        info["content"], key=lambda x: getattr(x, "updated_at"), reverse=True
    )[:12]

    return info


@app.context_processor
def inject_via():
    # inject the 'via' query param into the page (easier than parsing the querystring in JS)
    # so that we can track it with GA
    if request and request.args.get("via"):
        return {"via_tag": request.args.get("via").strip()}
    return {"via_tag": None}


@app.context_processor
def inject_free_before_year():
    # inject the year before which premium content is free
    if request:
        return {"free_before_date": app.config["PREMIUM_FREE_BEFORE"]}
    return {"free_before_date": None}


@app.route("/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def index():
    committee_meetings = load_from_api(
        "v2/committee-meetings/",
        fields=["id", "date", "title", "committee.name", "committee.house"],
        params={"per_page": 11},
    )["results"]
    bills = load_from_api("bill/current", return_everything=True)["results"]
    bills.sort(key=lambda b: b["updated_at"], reverse=True)
    questions = load_from_api(
        "v2/minister-questions/",
        fields=["id", "question_to_name", "question", "date"],
        params={"per_page": 11},
    )["results"]
    blogs = Post.query.order_by(desc(Post.date)).limit(6)

    return render_template(
        "index.html",
        committee_meetings=committee_meetings,
        bills=bills[:11],
        questions=questions,
        stock_pic="sa-parliament.jpg",
        featured_content=get_featured_content(),
        blogs=blogs,
    )


@app.route("/bills/")
def bills_portal():
    return render_template("bills/index.html")


@app.route("/bills/explained/")
def bills_explained():
    return render_template("bills/explained.html")


@app.route("/bills/<any(current):bill_type>/")
@app.route("/bills/<any(all, draft, pmb, tabled, 'pmb-committee'):bill_type>/")
@app.route(
    "/bills/<any(all, draft, pmb, tabled, 'pmb-committee'):bill_type>/year/<int:year>/"
)
def bills(bill_type, year=None):
    if bill_type == "current":
        # don't paginate by year
        year_list = None
        params = {}

    else:
        year_list = list(range(MIN_YEAR, date.today().year + 1))
        year_list.reverse()
        params = {}

        if not year:
            return redirect(url_for("bills", bill_type=bill_type, year=year_list[0]))

        if year not in year_list:
            abort(404)
        params["filter[year]"] = year

    if bill_type == "all":
        api_url = "bill"
    elif bill_type == "pmb-committee":
        api_url = "bill/pmb-committee"
    else:
        api_url = "bill/%s" % bill_type

    bills = load_from_api(api_url, return_everything=True, params=params)["results"]

    bills.sort(
        key=lambda b: [-b["year"], b["code"][0], b.get("number") or 0, b["title"]]
    )

    status_dict = {
        "na": ("in progress", "label-primary"),
        "ncop": ("in progress", "label-primary"),
        "assent": ("submitted to the president", "label-warning"),
        "enacted": ("signed into law", "label-success"),
        "withdrawn": ("withdrawn", "label-default"),
        "lapsed": ("lapsed", "label-default"),
    }

    return render_template(
        "bills/list.html",
        results=bills,
        status_dict=status_dict,
        year=year,
        year_list=year_list,
        bill_type=bill_type,
    )


@app.route("/bill/<int:bill_id>")
@app.route("/bill/<int:bill_id>/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def bill(bill_id):
    bill = load_from_api("v2/bills", bill_id)["result"]
    stages = {
        "enacted": "5",
        "president": "4",
        "ncop": "3",
        "returned-to-na": "3",
        "na": "2",
        "introduced": 1,
    }
    history = bill_history(bill)

    if bill.get("status"):
        social_summary = (
            bill["code"]
            + ", introduced "
            + pretty_date(bill["date_of_introduction"], "long")
            + ". "
            + bill["status"]["description"]
        )
    else:
        social_summary = (
            bill["code"]
            + ", introduced "
            + pretty_date(bill["date_of_introduction"], "long")
        )
    return render_template(
        "bills/detail.html",
        bill=bill,
        history=history,
        stages=stages,
        social_summary=social_summary,
        admin_edit_url=admin_url("bill", bill_id),
    )


@app.route("/committee/<int:committee_id>")
@app.route("/committee/<int:committee_id>/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def committee_detail(committee_id):
    """
    Display all available detail for the committee.
    """
    committee = load_from_api("v2/committees", committee_id)["result"]
    links = committee["_links"]
    filtered_meetings = {}

    # calls for comment
    committee["calls_for_comments"] = load_from_api(
        links["calls_for_comment"],
        fields=["id", "title", "start_date"],
        return_everything=True,
    )["results"]

    # tabled reports
    committee["tabled_committee_reports"] = load_from_api(
        links["tabled_reports"],
        fields=["id", "title", "start_date"],
        return_everything=True,
    )["results"]

    # memberships
    membership = load_from_api(links["members"], return_everything=True)["results"]
    sorter = lambda x: x["member"]["name"]
    membership = sorted(
        [m for m in membership if m["chairperson"]], key=sorter
    ) + sorted(
        [m for m in membership if not m["chairperson"]], key=sorter
    )  # noqa

    minister = committee.get("minister")
    recent_questions = []
    if minister:
        recent_questions = load_from_api(
            "minister-questions-combined",
            params={"filter[minister_id]": minister["id"]},
        )["results"]

    # meetings
    all_meetings = load_from_api(
        links["meetings"], fields=["id", "title", "date"], return_everything=True
    )["results"]

    for meeting in all_meetings:
        d = meeting["parsed_date"] = datetime.strptime(meeting["date"][:10], "%Y-%m-%d")
        if d.year not in filtered_meetings:
            filtered_meetings[d.year] = []
        filtered_meetings[d.year].append(meeting)

    latest_year = max(y for y in filtered_meetings) if filtered_meetings else None
    earliest_year = min(y for y in filtered_meetings) if filtered_meetings else None
    now = datetime.now()
    six_months = timedelta(days=30 * 6)  # 6 months
    filtered_meetings["six-months"] = [
        m for m in all_meetings if (now - m["parsed_date"]) <= six_months
    ]

    if filtered_meetings["six-months"]:
        starting_filter = "six-months"
    else:
        starting_filter = latest_year

    social_summary = (
        "Meetings, calls for comment, reports, and questions and replies of the "
        + committee["name"]
        + " committee."
    )
    current_attendance_summary = CommitteeMeetingAttendance.committee_attendence_trends(
        committee_id, "current"
    )
    historical_attendance_summary = (
        CommitteeMeetingAttendance.committee_attendence_trends(
            committee_id, "historical"
        )
    )

    if current_attendance_summary and committee["house"]["short_name"] != "Joint":
        year = current_attendance_summary[-1].year
        cte = Committee.query.get(committee_id)
        attendance_rank = (
            CommitteeMeetingAttendance.annual_attendance_rank_for_committee(
                cte, int(year)
            )
        )
    else:
        attendance_rank = None

    cte = Committee.query.get(committee_id)
    if cte:
        committee_petitions = []
        for petition in cte.petitions.all():
            petition_data = {
                'id': petition.id,
                'title': petition.title,
                'date': petition.date.isoformat() if petition.date else None,
                'issue': petition.issue,
                'status': {'name': petition.status.name} if petition.status else None
            }
            committee_petitions.append(petition_data)
        
        committee['petitions'] = committee_petitions
    else:
        committee['petitions'] = []

    bills = load_from_api(
        "v2/committees/%s/bills" % committee_id,
        fields=["id", "title", "status", "date_of_introduction", "code"],
    )["results"]

    bills.sort(key=lambda b: b["date_of_introduction"] or "", reverse=True)

    # If the request came from a Provincial Committee page,
    # pass the slug to the template to build the correct breadcrumbs
    from_page = request.args.get("from_page")
    return render_template(
        "committee_detail.html",
        current_year=now.year,
        earliest_year=earliest_year,
        filtered_meetings=filtered_meetings,
        committee=committee,
        membership=membership,
        has_meetings=len(all_meetings) > 0,
        starting_filter=starting_filter,
        recent_questions=recent_questions,
        social_summary=social_summary,
        current_attendance_summary=current_attendance_summary,
        historical_attendance_summary=historical_attendance_summary,
        attendance_rank=attendance_rank,
        admin_edit_url=admin_url("committee", committee_id),
        bills=bills,
        from_page=from_page
    )


@app.route("/committee/<int:committee_id>/follow-cte")
@app.route("/committee/<int:committee_id>/follow-cte/")
def committee_detail_follow_cte(committee_id):
    follow_committee(committee_id)
    flash(
        "You're now following this committee and "
        "we'll send you email alerts when new content is posted.",
        "success",
    )

    return redirect(url_for("committee_detail", committee_id=committee_id))


@app.route("/archived-attendance-overview")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def archived_attendance_overview():
    """
    Show archived attendance view
    """
    this_year = 2019
    last_year = 2018
    attendance = CommitteeMeetingAttendance.annual_attendance_trends(
        period="historical"
    )
    # index by year and cte id
    years = {
        year: {
            cte_id: list(cte_group)[0]
            for cte_id, cte_group in groupby(group, lambda r: r.committee_id)
        }
        for year, group in groupby(attendance, lambda r: r.year)
    }

    attendance = {
        "NA": [],
        "NCOP": [],
    }

    for cte in Committee.list().all():
        curr = years.get(this_year, {}).get(cte.id)
        prev = years.get(last_year, {}).get(cte.id)

        if cte.house.sphere != "national":
            continue
        if not curr or cte.ad_hoc or cte.house.name_short == "Joint":
            continue

        attendance[cte.house.name_short].append(
            {
                "committee": cte.name,
                "committee_id": cte.id,
                "n_meetings": curr.n_meetings,
                "avg_attendance": curr.avg_attendance * 100,
                "change": (curr.avg_attendance - (prev.avg_attendance if prev else 0))
                * 100,
            }
        )

    # rank them
    for att in list(attendance.values()):
        att.sort(key=lambda a: a["avg_attendance"], reverse=True)
        for i, item in enumerate(att):
            att[i]["rank"] = len(att) - i

    return render_template(
        "archive_attendance_overview.html",
        year=this_year,
        attendance_na=attendance["NA"],
        attendance_ncop=attendance["NCOP"],
    )
    pass


@app.route("/attendance-overview")
@cache.memoize(
    unless=lambda: should_skip_cache(request, current_user),
    make_name=lambda fname: cache_key(request),
)
def attendance_overview():
    """
    Display overview of attendance for meetings.
    """
    this_year = datetime.today().year
    last_year = this_year - 1
    attendance = CommitteeMeetingAttendance.annual_attendance_trends(to_year=this_year)

    years = {
        year: {
            cte_id: list(cte_group)[0]
            for cte_id, cte_group in groupby(group, lambda r: r.committee_id)
        }
        for year, group in groupby(attendance, lambda r: r.year)
    }

    attendance = {"NA": [], "NCOP": []}

    for cte in Committee.list().all():
        curr = years.get(this_year, {}).get(cte.id)
        prev = years.get(last_year, {}).get(cte.id)

        if cte.house.sphere != "national":
            continue
        if not curr or cte.ad_hoc or cte.house.name_short == "Joint":
            continue

        attendance[cte.house.name_short].append(
            {
                "committee": cte.name,
                "committee_id": cte.id,
                "n_meetings": curr.n_meetings,
                "avg_attendance": curr.avg_attendance * 100,
                "change": (curr.avg_attendance - (prev.avg_attendance if prev else 0))
                * 100,
            }
        )

    # rank them
    for att in list(attendance.values()):
        att.sort(key=lambda a: a["avg_attendance"], reverse=True)
        for i, item in enumerate(att):
            att[i]["rank"] = len(att) - i

    total_years = len(list(years.keys()))
    return render_template(
        "attendance_overview.html",
        year=this_year,
        last_year=last_year,
        total_years=total_years,
        attendance_na=attendance["NA"],
        attendance_ncop=attendance["NCOP"],
    )


@app.route("/committee-question/<int:question_id>/")
def committee_question(question_id):
    """Display a single committee question."""
    question = load_from_api("v2/minister-questions", question_id)["result"]
    minister = question["minister"]
    if minister:
        committee = minister.get("committee", {"house": {}, "id": 0})
    else:
        committee = None
    if question["question_to_name"]:
        question_to_name = question["question_to_name"]
    else:
        question_to_name = "[UNKNOWN]"
    if question["asked_by_name"]:
        asked_by_name = question["asked_by_name"]
    else:
        asked_by_name = "[UNKNOWN]"
    social_summary = (
        "A question to the "
        + question_to_name
        + ", asked on "
        + pretty_date(question["date"], "long")
        + " by "
        + asked_by_name
    )

    return render_template(
        "committee_question.html",
        minister=minister,
        committee=committee,
        question=question,
        hide_replies=False,
        content_date=question["date"],
        social_summary=social_summary,
        admin_edit_url=admin_url("committee-question", question_id),
    )


@app.route("/committees/")
def committees():
    """
    Page through all available committees.
    """
    committees = load_from_api(
        "v2/committees",
        return_everything=True,
        fields=[
            "id",
            "name",
            "premium",
            "ad_hoc",
            "active",
            "monitored",
            "house",
            "last_active_year",
        ],
    )["results"]

    nat = {"name": "National Assembly", "committees": []}
    ncp = {"name": "National Council of Provinces", "committees": []}
    jnt = {"name": "Joint Committees", "committees": []}

    adhoc_committees = OrderedDict((("nat", nat), ("ncp", ncp), ("jnt", jnt)))
    reg_committees = deepcopy(adhoc_committees)
    wc_committees = OrderedDict(())

    committees_type = None

    for committee in committees:
        if committee["house"]["sphere"] == "provincial":
            # For Provincial Legislatures, we only show Western Cape committees
            if committee["house"]["short_name"] == "WC":
                house = committee["house"]
                if house["short_name"] not in wc_committees:
                    wc_committees[house["short_name"]] = {
                        "name": house["name"],
                        "committees": [],
                    }
                committees_type = wc_committees
            else:
                continue

        elif committee["ad_hoc"] is True:
            committees_type = adhoc_committees
        else:
            committees_type = reg_committees

        if current_user.is_authenticated:
            user_following = current_user.following

            # Check if user is following committee
            if current_user.is_authenticated and committee["id"] in [
                ufc.id for ufc in user_following
            ]:
                committee["followed"] = True

        if committee["house"]:
            if committee["house"]["id"] is House.NATIONAL_ASSEMBLY:
                committees_type["nat"]["committees"].append(committee)
            elif committee["house"]["id"] is House.NAT_COUNCIL_OF_PROV:
                committees_type["ncp"]["committees"].append(committee)
            elif committee["house"]["id"] is House.JOINT_COMMITTEE:
                committees_type["jnt"]["committees"].append(committee)
            elif committee["house"]["sphere"] == "provincial":
                # Only show monitored committees
                if committee["monitored"] == True:
                    committees_type[house["short_name"]]["committees"].append(committee)

    for typ in list(adhoc_committees.values()):
        typ["committees"].sort(key=lambda x: (not x["active"], x["name"]))

    for typ in list(wc_committees.values()):
        typ["committees"].sort(key=lambda x: (not x["active"], x["name"]))

    return render_template(
        "committee_list.html",
        reg_committees=reg_committees,
        adhoc_committees=adhoc_committees,
        wc_committees=wc_committees,
    )


def sort_houses(houses):
    sorted_houses = []
    houses_dict = OrderedDict()
    for house in houses:
        houses_dict[house.id] = house
    sorted_houses.append(houses_dict.pop(House.NATIONAL_ASSEMBLY))
    sorted_houses.append(houses_dict.pop(House.NAT_COUNCIL_OF_PROV))
    sorted_houses.append(houses_dict.pop(House.JOINT_COMMITTEE))
    for house in list(houses_dict.values()):
        sorted_houses.append(house)
    return sorted_houses


@app.route("/committee-meetings/")
@app.route("/committee-meetings/<int:page>/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def committee_meetings(page=0):
    """
    Page through all available committee meetings.
    """
    committees = load_from_api("committee", return_everything=True)["results"]
    houses = sort_houses(House.query.all())
    filters = {"committee": None}
    params = {}

    if request.args.get("filter[committee]"):
        filters["committee"] = params["filter[committee_id]"] = request.args.get(
            "filter[committee]"
        )

    committee_meetings_list = load_from_api(
        "committee-meeting", page=page, params=params
    )
    committee_meetings = committee_meetings_list["results"]
    count = committee_meetings_list["count"]

    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    url = "/committee-meetings"
    return render_template(
        "list.html",
        results=committee_meetings,
        num_pages=num_pages,
        page=page,
        url=url,
        title="Committee Meeting Reports",
        content_type="committee-meeting",
        icon="comment",
        committees=committees,
        houses=houses,
        filters=filters,
    )


@app.route("/committee-meeting/<int:event_id>")
@app.route("/committee-meeting/<int:event_id>/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def committee_meeting(event_id):
    """
    Display committee meeting details, including report and any other related content.
    """

    event = load_from_api("v2/committee-meetings", event_id)["result"]

    if event.get("premium_content_excluded"):
        premium_committees = load_from_api("committee/premium", return_everything=True)[
            "results"
        ]
    else:
        premium_committees = None

    audio, related_docs = classify_attachments(event.get("files", []))

    attendance = load_from_api(
        "v2/committee-meetings/%s/attendance" % event_id, return_everything=True
    )["results"]
    attendance = [
        a
        for a in attendance
        if a["attendance"] in CommitteeMeetingAttendance.ATTENDANCE_CODES_PRESENT
    ]
    sorter = lambda x: x["member"]["name"]
    attendance = sorted(
        [a for a in attendance if a["chairperson"]], key=sorter
    ) + sorted(
        [a for a in attendance if not a["chairperson"]], key=sorter
    )  # noqa
    if event["committee"]:
        event_committee_name = event["committee"]["name"]
    else:
        event_committee_name = "[UNKNOWN COMMITTEE]"
    if event["chairperson"]:
        social_summary = (
            "A meeting of the "
            + event_committee_name
            + " committee held on "
            + pretty_date(event["date"], "long")
            + ", lead by "
            + event["chairperson"]
        )
    else:
        social_summary = (
            "A meeting of the "
            + event_committee_name
            + " committee held on "
            + pretty_date(event["date"], "long")
            + "."
        )

    return render_template(
        "committee_meeting.html",
        event=event,
        committee=event["committee"],
        audio=audio,
        related_docs=related_docs,
        attendance=attendance,
        premium_committees=premium_committees,
        content_date=event["date"],
        social_summary=social_summary,
        admin_edit_url=admin_url("committee-meeting", event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config["SOUNDCLOUD_APP_KEY_ID"],
    )


@app.route("/committee-meeting/<int:event_id>/follow-cte")
@app.route("/committee-meeting/<int:event_id>/follow-cte/")
def committee_meeting_follow_cte(event_id):
    event = load_from_api("v2/committee-meetings", event_id)["result"]
    follow_committee(event["committee_id"])

    flash(
        "You're now following this committee and "
        "we'll send you email alerts when new content is posted.",
        "success",
    )

    return redirect(url_for("committee_meeting", event_id=event_id))


@app.route("/tabled-committee-reports/")
@app.route("/tabled-committee-reports/<int:page>/")
def tabled_committee_reports(page=0):
    """
    Page through all available tabled-committee-reports.
    """

    logger.debug("tabled-committee-reports page called")
    houses = sort_houses(House.query.all())
    committees = load_from_api("committee", return_everything=True)["results"]
    filters = {}
    params = {}
    filters["committee"] = params["filter[committee_id]"] = request.args.get(
        "filter[committee]"
    )
    tabled_committee_reports_list = load_from_api(
        "tabled-committee-report", page=page, params=params
    )
    count = tabled_committee_reports_list["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    tabled_committee_reports = tabled_committee_reports_list["results"]
    url = "/tabled-committee-reports"
    return render_template(
        "list.html",
        results=tabled_committee_reports,
        content_type="tabled_committee_report",
        title="Tabled Committee Reports",
        num_pages=num_pages,
        page=page,
        url=url,
        houses=houses,
        icon="briefcase",
        committees=committees,
        filters=filters,
    )


@app.route("/tabled-committee-report/<int:tabled_committee_report_id>")
@app.route("/tabled-committee-report/<int:tabled_committee_report_id>/")
def tabled_committee_report(tabled_committee_report_id):
    """
    Tabled Committee Report
    """
    logger.debug("tabled-committee-report page called")
    tabled_committee_report = load_from_api(
        "tabled-committee-report", tabled_committee_report_id
    )
    logger.debug(tabled_committee_report)
    return render_template(
        "tabled_committee_report_detail.html",
        tabled_committee_report=tabled_committee_report,
        content_date=tabled_committee_report["start_date"],
        admin_edit_url=admin_url("tabled-committee-report", tabled_committee_report_id),
    )


@app.route("/calls-for-comments/")
@app.route("/calls-for-comments/<int:page>/")
def calls_for_comments(page=0):
    """
    Page through all available calls-for-comments.
    """

    logger.debug("calls-for-comments page called")
    committees = load_from_api("committee", return_everything=True)["results"]
    # For PLs, only show WC:
    committees[:] = [
        c
        for c in committees
        if not (
            c["house"]["sphere"] == "provincial" and c["house"]["name_short"] != "WC"
        )
    ]

    houses = sort_houses(House.query.all())
    filters = {}
    params = {}
    per_page = app.config["RESULTS_PER_PAGE"]
    filters["committee"] = params["filter[committee_id]"] = request.args.get(
        "filter[committee]"
    )

    call_for_comment_list = load_from_api(
        "v2/calls-for-comments", page=page, params=params, pagesize=per_page
    )

    count = call_for_comment_list["count"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    calls_for_comments = sorted(
        call_for_comment_list["results"],
        key=lambda x: x["end_date"] or "",
        reverse=True,
    )

    open_calls = [c for c in calls_for_comments if not c["closed"] and c["end_date"]]
    closed_calls = [c for c in calls_for_comments if c["closed"] or not c["end_date"]]

    url = "/calls-for-comments"
    return render_template(
        "list.html",
        results=calls_for_comments,
        num_pages=num_pages,
        page=page,
        url=url,
        houses=houses,
        icon="comments",
        content_type="call_for_comment",
        title="Calls for Comments",
        committees=committees,
        filters=filters,
        open_calls=open_calls,
        closed_calls=closed_calls,
    )


@app.route("/call-for-comment/<int:call_for_comment_id>")
@app.route("/call-for-comment/<int:call_for_comment_id>/")
def call_for_comment(call_for_comment_id):
    """
    Tabled Committee Report
    """
    logger.debug("call-for-comment page called")
    call_for_comment = load_from_api("v2/calls-for-comments", call_for_comment_id)[
        "result"
    ]
    logger.debug(call_for_comment)

    if call_for_comment["committee"]:
        cfc_committee = (
            "A call for comments by the "
            + call_for_comment["committee"]["name"]
            + " committee. "
        )
    else:
        cfc_committee = "A call for comments. "
    if call_for_comment["end_date"]:
        cfc_deadline = "Submissions must be received by no later than " + pretty_date(
            call_for_comment["end_date"], "long"
        )
        if call_for_comment["closed"]:
            cfc_deadline = "Submissions closed " + pretty_date(
                call_for_comment["end_date"], "long"
            )
    else:
        cfc_deadline = ""

    social_summary = cfc_committee + cfc_deadline

    return render_template(
        "call_for_comment_detail.html",
        call_for_comment=call_for_comment,
        content_date=call_for_comment["start_date"],
        social_summary=social_summary,
        admin_edit_url=admin_url("call-for-comment", call_for_comment_id),
    )


@app.route("/call-for-comment/<int:call_for_comment_id>/follow-cte")
@app.route("/call-for-comment/<int:call_for_comment_id>/follow-cte/")
def call_for_comment_follow_cte(call_for_comment_id):
    call_for_comment = load_from_api("v2/calls-for-comments", call_for_comment_id)[
        "result"
    ]
    follow_committee(call_for_comment["committee_id"])

    flash(
        "You're now following this committee and "
        "we'll send you email alerts when new content is posted.",
        "success",
    )

    return redirect(
        url_for("call_for_comment", call_for_comment_id=call_for_comment_id)
    )


@app.route("/policy-documents/")
@app.route("/policy-documents/<int:page>/")
def policy_documents(page=0):
    """
    Page through all available policy-documents.
    """

    logger.debug("policy-documents page called")
    policy_documents_list = load_from_api("policy-document", page=page)
    count = policy_documents_list["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    policy_documents = policy_documents_list["results"]
    url = "/policy-documents"
    return render_template(
        "list.html",
        results=policy_documents,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="file-text-o",
        content_type="policy_document",
        title="Policy Documents",
    )


@app.route("/policy-document/<int:policy_document_id>")
@app.route("/policy-document/<int:policy_document_id>/")
def policy_document(policy_document_id):
    """
    Policy Document
    """
    logger.debug("policy-document page called")
    policy_document = load_from_api("policy-document", policy_document_id)
    logger.debug(policy_document)
    return render_template(
        "policy_document_detail.html",
        policy_document=policy_document,
        content_date=policy_document["start_date"],
        admin_edit_url=admin_url("policy", policy_document_id),
    )


@app.route("/gazettes/")
@app.route("/gazettes/<int:page>/")
def gazettes(page=0):
    """
    Page through all available gazettes.
    """

    logger.debug("gazettes page called")
    gazettes_list = load_from_api("gazette", page=page)
    count = gazettes_list["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    gazettes = gazettes_list["results"]
    url = "/gazettes"
    return render_template(
        "list.html",
        results=gazettes,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="file-text-o",
        content_type="gazette",
        title="Gazettes",
    )


@app.route("/gazette/<int:gazette_id>")
@app.route("/gazette/<int:gazette_id>/")
def gazette(gazette_id):
    """
    Policy Document
    """
    logger.debug("gazette page called")
    gazette = load_from_api("gazette", gazette_id)
    logger.debug(gazette)
    return render_template(
        "gazette_detail.html",
        gazette=gazette,
        content_date=gazette["start_date"],
        admin_edit_url=admin_url("gazette", gazette_id),
    )


@app.route("/members/")
def members():
    """All MPs."""
    members = load_from_api("v2/members", return_everything=True)["results"]

    # partition by house
    members_by_house = {}
    for member in members:
        if (
            member.get("house")
            and member["current"]
            and member["house"]["sphere"] == "national"
        ):
            members_by_house.setdefault(member["house"]["name"], []).append(member)
    id_mapping = {house: slugify(house) for house in list(members_by_house.keys())}

    return render_template(
        "member_list.html", members_by_house=members_by_house, id_mapping=id_mapping
    )


@app.route("/member/<int:member_id>")
@app.route("/member/<int:member_id>/")
def member(member_id):
    logger.debug("member page called")
    member = load_from_api("member", member_id)
    return render_template(
        "member_detail.html",
        member=member,
        admin_edit_url=admin_url("member", member_id),
    )


@app.route("/hansard/<int:event_id>")
@app.route("/hansard/<int:event_id>/")
def hansard(event_id):
    event = load_from_api("hansard", event_id)
    audio, related_docs = classify_attachments(event.get("files", []))

    return render_template(
        "hansard_detail.html",
        event=event,
        audio=audio,
        related_docs=related_docs,
        content_date=event["date"],
        admin_edit_url=admin_url("hansard", event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config["SOUNDCLOUD_APP_KEY_ID"],
    )


@app.route("/hansards/")
@app.route("/hansards/<int:page>/")
def hansards(page=0):
    """
    Page through all available hansards.
    """

    logger.debug("hansards page called")

    params = {}
    house_id = request.args.get("filter[house_id]", None)
    year = request.args.get("filter[year]", None)

    if house_id is not None:
        params["filter[house_id]"] = house_id
        house_id = int(house_id)
    if year is not None:
        params["filter[year]"] = year
        year = int(year)

    year_list = list(range(MIN_YEAR, date.today().year + 1))
    year_list.reverse()

    hansards_list = load_from_api("hansard", page=page, params=params)
    houses = sort_houses(
        House.query.filter(House.sphere == "national", House.name_short != "President")
    )

    count = hansards_list["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    hansards = hansards_list["results"]
    url = "/hansards"

    return render_template(
        "list.html",
        results=hansards,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="archive",
        title="Hansards",
        content_type="hansard",
        selected_house=house_id,
        selected_year=year,
        houses=houses,
        year_list=year_list,
    )


@app.route("/provincial-legislatures/")
def provincial_legislatures_list():
    """
    A page with links to the provincial legislatures
    """
    prov_legislatures = (
        House.query.filter(House.sphere == "provincial")
        .order_by(desc(House.name))
        .all()
    )
    provinces = [
        {"name": p.name, "slug": utils.slugify_province(p.name)}
        for p in prov_legislatures
    ]

    return render_template("provincial/list.html", provinces=provinces)


@app.route("/provincial-legislatures/<slug>/")
def provincial_legislatures_detail(slug):
    """
    A page showing the information on the selected provincial parliament
    Except: WC
    """
    province = House.query.filter(House.name == utils.deslugify_province(slug)).first()
    if not province:
        abort(404)

    if slug == "western-cape":
        return provincial_legislatures_western_cape(slug, province)

    # Provincial programmes are stored as daily schedules
    # We only show the latest
    provincial_programmes = load_from_api(
        "v2/daily-schedules",
        return_everything=True,
        params={"filter[house]": province.name_short},
    )["results"]
    latest_programme = provincial_programmes[0] if provincial_programmes else None

    committees = load_from_api("v2/committees", return_everything=True)["results"]
    provincial_committees = [
        c for c in committees if c["house"]["short_name"] == province.name_short
    ]
    # Show monitored committees first
    provincial_committees.sort(key=lambda c: [-c["monitored"], c["name"]])

    # Members
    members = load_from_api(
        "v2/members",
        return_everything=True,
        params={"filter[house]": province.name_short},
    )["results"]
    mpls = []
    for member in members:
        if (
            member.get("house")
            and member["current"]
            and member["house"]["short_name"] == province.name_short
        ):
            mpls.append(member)

    if province.speaker_id:
        speaker = load_from_api("v2/members", province.speaker_id)["result"]
    else:
        speaker = None

    pa_members_url = "https://www.pa.org.za/place/%s/" % (slug)
    pa_offices_url = "https://www.pa.org.za/place/%s/places/" % (slug)

    return render_template(
        "provincial/detail.html",
        province=province,
        slug=slug,
        speaker=speaker,
        latest_programme=latest_programme,
        provincial_committees=provincial_committees[0:6],
        mpls=mpls[0:6],
        pa_members_url=pa_members_url,
        pa_offices_url=pa_offices_url,
        admin_edit_url=admin_url("provincial-legislatures", province.id),
    )


def provincial_legislatures_western_cape(slug, province):
    members = load_from_api("v2/members", return_everything=True)["results"]

    # members of provincial parliament
    mpls = []
    for member in members:
        if (
            member.get("house")
            and member["current"]
            and member["house"]["short_name"] == "WC"
        ):
            mpls.append(member)

    if province.speaker_id:
        speaker = load_from_api("v2/members", province.speaker_id)["result"]
    else:
        speaker = None

    # provincial committees
    committees = load_from_api("v2/committees", return_everything=True)["results"]
    # Only show monitored committees:
    committees[:] = [c for c in committees if c["monitored"] == True]

    provincial_committees = []

    for committee in committees:
        if committee["house"]["short_name"] == "WC":
            provincial_committees.append(committee)

    # provincial calls for comments that are currently open
    provincial_calls_for_comment = load_from_api(
        "v2/calls-for-comments",
        return_everything=True,
        fields=["id", "title", "closed", "end_date", "start_date"],
        params={"filter[house]": "WC"},
    )["results"]
    provincial_calls_for_comment = [
        c for c in provincial_calls_for_comment if c["end_date"] and not c["closed"]
    ]

    provincial_programmes = load_from_api(
        "v2/daily-schedules", return_everything=True, params={"filter[house]": "WC"}
    )["results"]
    latest_programme = provincial_programmes[0] if provincial_programmes else None

    return render_template(
        "provincial/western_cape.html",
        province=province,
        slug=slug,
        speaker=speaker,
        mpls=mpls[0:6],
        provincial_committees=provincial_committees[0:6],
        provincial_calls_for_comment=provincial_calls_for_comment,
        latest_programme=latest_programme,
        admin_edit_url=admin_url("provincial-legislatures", province.id),
    )


@app.route("/provincial-parliaments/<slug>/")
def provincial_parliaments_old(slug):
    """
    Redirect to new URL: `provincial-parliaments` -> `provincial-legislatures`
    """
    return redirect(url_for("provincial_legislatures_detail", slug=slug))


@app.route("/provincial-legislatures/<slug>/committees/")
def provincial_committees(slug):
    province = House.query.filter(House.name == utils.deslugify_province(slug)).first()
    # TODO Filtering is not working as expected.
    # House is not joined.
    committees = load_from_api(
        "v2/committees",
        return_everything=True,
        params={"filter[house]": province.name_short},
    )["results"]

    provincial_committees = [
        c for c in committees if c["house"]["short_name"] == province.name_short
    ]

    return render_template(
        "provincial/committee_list.html",
        province=province,
        slug=slug,
        provincial_committees=provincial_committees,
    )


@app.route("/provincial-legislatures/<slug>/members/")
def provincial_members(slug):
    province = House.query.filter(House.name == utils.deslugify_province(slug)).first()
    members = load_from_api("v2/members", return_everything=True)["results"]

    provincial_members = [
        m
        for m in members
        if m.get("house")
        and m["current"]
        and m["house"]["short_name"] == province.name_short
    ]

    return render_template(
        "member_list.html",
        province=province,
        slug=slug,
        provincial_members=provincial_members,
    )


@app.route("/members/western-cape/")
def western_cape_members():
    """
    Redirect to new URL:
    `/members/western-cape/` -> `provincial-legislatures/western-cape/members/`
    """
    slug = "western-cape"
    return redirect(url_for("provincial_members", slug=slug))


@app.route("/briefing/<int:event_id>")
@app.route("/briefing/<int:event_id>/")
def briefing(event_id):

    event = load_from_api("briefing", event_id)
    audio, related_docs = classify_attachments(event.get("files", []))

    return render_template(
        "briefing_detail.html",
        event=event,
        audio=audio,
        related_docs=related_docs,
        content_date=event["date"],
        admin_edit_url=admin_url("briefing", event_id),
        SOUNDCLOUD_APP_KEY_ID=app.config["SOUNDCLOUD_APP_KEY_ID"],
    )


@app.route("/briefings/")
@app.route("/briefings/<int:page>/")
def briefings(page=0):
    """
    Page through all available briefings.
    """

    logger.debug("briefings page called")
    briefings_list = load_from_api("briefing", page=page)
    count = briefings_list["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    briefings = briefings_list["results"]
    url = "/briefings"
    return render_template(
        "list.html",
        results=briefings,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="bullhorn",
        title="Media Briefings",
        content_type="briefing",
    )


@app.route("/daily-schedule/<int:daily_schedule_id>")
@app.route("/daily-schedule/<int:daily_schedule_id>/")
def daily_schedule(daily_schedule_id):
    daily_schedule = load_from_api("v2/daily-schedules", daily_schedule_id)["result"]
    return render_template(
        "daily_schedule_detail.html",
        daily_schedule=daily_schedule,
        admin_edit_url=admin_url("schedule", daily_schedule_id),
    )


@app.route("/daily-schedules/")
@app.route("/daily-schedules/<int:page>/")
def daily_schedules(page=0):
    """
    Page through all available daily_schedules.
    """

    per_page = app.config["RESULTS_PER_PAGE"]
    daily_schedules_list = load_from_api(
        "v2/daily-schedules",
        page=page,
        pagesize=per_page,
        params={"filter[exclude_sphere]": "provincial"},
    )
    count = daily_schedules_list["count"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    daily_schedules = daily_schedules_list["results"]
    url = "/daily-schedules"
    return render_template(
        "list.html",
        results=daily_schedules,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="calendar",
        title="Daily Schedules",
        content_type="daily_schedule",
    )


@app.route("/provincial-legislatures/<slug>/programme/<int:programme_id>")
@app.route("/provincial-legislatures/<slug>/programme/<int:programme_id>/")
def provincial_programme(slug, programme_id):
    """
    Provincial programmes are stored as daily schedules
    """
    province = House.query.filter(House.name == utils.deslugify_province(slug)).first()
    if not province:
        abort(404)

    provincial_programme = load_from_api("v2/daily-schedules", programme_id)["result"]
    return render_template(
        "provincial_programme_detail.html",
        province=province,
        slug=slug,
        provincial_programme=provincial_programme,
        admin_edit_url=admin_url("schedule", programme_id),
    )


@app.route("/provincial-legislatures/<slug>/programmes/")
@app.route("/provincial-legislatures/<slug>/programmes/<int:page>/")
def provincial_programmes(slug, page=0):
    """
    List of all programmes for a PL
    """
    province = House.query.filter(House.name == utils.deslugify_province(slug)).first()
    if not province:
        abort(404)

    per_page = app.config["RESULTS_PER_PAGE"]
    programmes_list = load_from_api(
        "v2/daily-schedules",
        page=page,
        pagesize=per_page,
        params={"filter[house]": province.name_short},
    )
    count = programmes_list["count"]
    num_pages = int(math.ceil(float(count) / float(per_page)))
    programmes = programmes_list["results"]

    return render_template(
        "list.html",
        results=programmes,
        num_pages=num_pages,
        page=page,
        icon="calendar",
        title="Programmes",
        province=province,
        slug=slug,
        content_type="provincial_programme",
    )


@app.route("/question_reply/<int:question_reply_id>")
@app.route("/question_reply/<int:question_reply_id>/")
def question_reply(question_reply_id):
    question_reply = load_from_api("v2/minister-questions/legacy", question_reply_id)[
        "result"
    ]
    minister = question_reply.get("minister") or {}
    committee = minister.get("committee")

    return render_template(
        "question_reply_detail.html",
        question_reply=question_reply,
        minister=minister,
        committee=committee,
        content_date=question_reply["start_date"],
        admin_edit_url=admin_url("question", question_reply_id),
    )


@app.route("/question_replies/")
@app.route("/question_replies/<int:page>/")
def question_replies(page=0):
    """
    Page through all available question_replies + committee_questions.
    """
    logger.debug("question_replies page called")
    ministers = load_from_api("v2/ministers", return_everything=True)["results"]
    filters = {}
    params = {}
    year = request.args.get("filter[year]", None)
    if year is not None:
        filters["year"] = params["filter[year]"] = year
        year = int(year)
    filters["minister"] = params["filter[minister_id]"] = request.args.get(
        "filter[minister]"
    )
    questions = load_from_api("minister-questions-combined", page=page, params=params)
    count = questions["count"]
    per_page = app.config["RESULTS_PER_PAGE"]
    num_pages = int(math.ceil(float(count) / float(per_page)))

    # sort ministers to put President first
    ministers.sort(key=lambda m: "" if m["name"] == "President" else m["name"])

    year_list = list(range(MIN_YEAR, date.today().year + 1))
    year_list.reverse()

    return render_template(
        "question_list.html",
        questions=questions,
        hide_replies=True,
        url="/question_replies",
        num_pages=num_pages,
        per_page=per_page,
        page=page,
        icon="question-circle",
        title="Questions and Replies",
        content_type="minister_question",
        ministers=ministers,
        all_committees_option="All Ministries",
        filters=filters,
        selected_year=year,
        year_list=year_list,
    )


@app.route("/search/")
@app.route("/search/<int:page>/")
@cache.memoize(
    make_name=lambda fname: cache_key(request),
    unless=lambda: should_skip_cache(request, current_user),
)
def search(page=0):
    """
    Display search page
    """
    filters = {}
    filters["type"] = request.args.get("filter[type]", "")
    filters["start_date"] = request.args.get("filter[start_date]", "")
    filters["end_date"] = request.args.get("filter[end_date]", "")
    filters["committee"] = request.args.get("filter[committee]", "")

    # support legacy search URLs that allowed "None" as a value
    for k, v in list(filters.items()):
        if v == "None":
            filters[k] = None

    # ensure decently encoded unicode strings. this is required because
    # we can't pass unicode to urllib3, which is super lame. This is only
    # a problem for search queries with unicode, which will be transliterated
    # in any case.
    q = unidecode(request.args.get("q", "").strip())

    params = dict(filters)
    params["q"] = q
    params["page"] = page

    # do the search
    search = {}
    try:
        if q:
            search = load_from_api("search", params=params)
    except ApiException as e:
        if e.code == 422:
            # bad search, eg: "   "
            q = ""
        else:
            raise e

    years = list(range(1997, datetime.now().year + 1))
    years.reverse()

    bincount = {}
    yearcount = {}
    if search:
        for bin in search["bincount"]["types"]:
            bincount[bin["key"]] = bin["doc_count"]

        for year in search["bincount"]["years"]:
            yearcount[int(year["key_as_string"][:4])] = year["doc_count"]

        search["friendly_data_type"] = Search.friendly_data_types.get(
            filters["type"], None
        )

    committees = load_from_api("committee", return_everything=True)["results"]
    houses = sort_houses(House.query.all())

    def search_url(**kwargs):
        args = dict(filters)
        args.update(kwargs)
        args = {("filter[%s]" % k): v for k, v in list(args.items()) if v}
        return url_for("search", q=q, **args)

    saved_search = None
    if not current_user.is_anonymous:
        saved_search = SavedSearch.find(
            current_user,
            q,
            content_type=filters["type"] or None,
            committee_id=filters["committee"] or None,
        )

    if filters["committee"]:
        for committee in committees:
            if committee["id"] == int(filters["committee"]):
                search["filtered_committee_name"] = committee["name"]
                break

    # suggest a phrase search?
    if q and '"' not in q and search["hits"] > 0:
        suggest_phrase = '"%s"' % q
        kwargs = {("filter[%s]" % k): v for k, v in list(filters.items()) if v}
        kwargs["q"] = suggest_phrase
        suggest_phrase_url = url_for("search", **kwargs)
    else:
        suggest_phrase = False
        suggest_phrase_url = None

    # suggest a broader search?
    if not suggest_phrase and q:
        if search["hits"] == 0:
            suggest_broader = True
        else:
            suggest_broader = False
    else:
        suggest_broader = False

    return render_template(
        "search.html",
        q=q,
        search=search,
        num_pages=search.get("pages"),
        page=search.get("page"),
        per_page=search.get("per_page"),
        search_url=search_url,
        url=url_for("search")[:-1],
        query_string=request.query_string,
        filters=filters,
        years=years,
        bincount=bincount,
        yearcount=yearcount,
        committees=committees,
        houses=houses,
        search_types=list(Search.friendly_data_types.items()),
        saved_search=saved_search,
        suggest_phrase=suggest_phrase,
        suggest_phrase_url=suggest_phrase_url,
        suggest_broader=suggest_broader,
    )


@app.route("/page/<path:pagename>")
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

    return render_template(
        "page.html",
        page=page,
        attachments=files,
        admin_edit_url=admin_url("pages", page.id),
    )


# Redirect to content stored in S3.
#
# For current content, we always have URLs like /files/the/file.pdf
# which must be redirected to S3/the/file.pdf.
#
# Legacy content from the old website can be under a few other paths, too.
#   /docs/foo
#   /questions/foo
#   /mp3/foo
@app.route("/<any(docs, mp3, questions):dir>/<path:path>")
@app.route("/files/<path:path>")
def docs(path, dir=""):
    if dir:
        dir = dir + "/"

    # report to google analytics
    try:
        utils.track_file_download()
    except Exception as e:
        logger.error("Error tracking pageview: %s" % e, exc_info=e)

    remote = app.config["STATIC_HOST"] + dir + path

    if request.args.get("direct") == "1":
        resp = requests.get(remote, stream=True)
        return Response(
            resp.iter_content(chunk_size=10 * 1024),
            content_type=resp.headers["Content-Type"],
        )

    return redirect(remote)


@app.route("/correct-this-page", methods=["POST"])
def correct_this_page():

    form = forms.CorrectThisPageForm(request.form)
    if form.validate():
        msg = Message(
            "Correct This Page feedback",
            recipients=["correct@pmg.org.za"],
            sender="info@pmg.org.za",
        )
        msg.html = render_template(
            "correct_this_page.html",
            submission={
                "url": form.url.data,
                "details": form.details.data,
                "email": form.email.data,
            },
        )
        try:
            mail.send(msg)
            data = {"status": "Ok"}
        except Exception as error:
            logger.exception(error)
            data = {"status": "emailError"}
        return jsonify(data)

    else:
        form_errors = {}
        for field, errors in list(form.errors.items()):
            for error in errors:
                if field == "recaptcha":
                    form_errors.update(
                        {"field": field, "error": "Please fill in the Recaptcha field"}
                    )
                else:
                    form_errors.update({"field": field, "error": error})
        data = {"status": "Error", "errors": form_errors}
        return jsonify(data)


@app.route("/blog")
@app.route("/blog/")
@app.route("/blog/<int:page>/")
def blog(page=0):
    per_page = 10
    filters = {}

    year = func.date_part("year", Post.date).label("year")
    month = func.date_part("month", Post.date).label("month")
    month_name = func.to_char(Post.date, "FMMonth").label("month_name")

    post_query = Post.query

    if request.args.get("filter[month]"):
        filters["month"] = request.args.get("filter[month]")
        post_query = post_query.filter(month_name == filters["month"])

    if request.args.get("filter[year]"):
        filters["year"] = request.args.get("filter[year]")
        post_query = post_query.filter(year == filters["year"])

    count = post_query.count()
    posts = (
        post_query.order_by(desc(Post.date))
        .limit(per_page)
        .offset(page * per_page)
        .all()
    )

    months = (
        db.session.query(
            month_name, month, year, func.count(Post.id).label("month_posts")
        )
        .group_by(text("year"), text("month"), text("month_name"))
        .order_by(year.desc(), month.asc())
        .subquery("months")
    )

    years = (
        db.session.query(
            cast(months.c.year, Integer).label("year"),
            func.sum(months.c.month_posts).label("year_posts"),
            func.array_agg(months.c.month).label("months"),
            func.array_agg(months.c.month_name).label("month_names"),
            func.array_agg(months.c.month_posts).label("month_posts"),
        )
        .group_by(text("year"))
        .order_by(desc(text("year")))
        .all()
    )

    next = create_next_page_url(count, page, per_page)
    num_pages = int(math.ceil(float(count) / float(per_page)))
    url = "/blog"
    return render_template(
        "/blog.html",
        filters=filters,
        posts=posts,
        years=years,
        num_pages=num_pages,
        page=page,
        per_page=per_page,
        url=url,
    )


@app.route("/blog/<path:slug>")
def blog_post(slug):
    slug = Post().validate_slug(None, slug)
    post = Post.query.filter(Post.slug == slug).first()
    if not post:
        abort(404)

    files = [f.file for f in post.files]

    social_summary = post.body

    if files:
        social_image = "/files" + files[0].file_path
    else:
        social_image = None

    return render_template(
        "blog_post.html",
        post=post,
        attachments=files,
        admin_edit_url=admin_url("posts", post.id),
        social_summary=social_summary,
        social_image=social_image,
    )

@app.route("/petitions/")
def petitions_home(): 
    return render_template("petitions/index.html")

@app.route("/petitions/all/")
@app.route("/petitions/current/")
def petitions(page=0):
    per_page = 1000
    query = Petition.query.order_by(Petition.date.desc())
    count = query.count()
    petitions = query.offset(page * per_page).limit(per_page).all()
    num_pages = int(math.ceil(float(count) / float(per_page)))
    url = "/petitions"
    return render_template(
        "petitions/list.html",   
        results=petitions,
        num_pages=num_pages,
        page=page,
        url=url,
        icon="file-text-o",   
        title="Petitions",
        content_type="petition",  
    )

@app.route("/petitions/explained")
def petitions_explained():
    return render_template("petitions/explained.html")

@app.route("/petitions/<int:petition_id>")
@app.route("/petitions/<int:petition_id>/")
def petition_detail(petition_id):
    petition = Petition.query.get_or_404(petition_id)
    

    # This is not good and should be reconsidered. 
    # It currently uses the ids as set in admin. Not a good idea.

    petition_stages = {
        3: "2",  # House (NA or NCOP)
        2: "3",  # Report published
        1: "4",  # Petition finalised
    }

    if petition.house == "National Assembly":
        house = "NA"
    else:
        house = "NCOP"

    return render_template(
        "petitions/detail.html",
        petition=petition,
        house=house,
        petition_stages=petition_stages,
        admin_edit_url=admin_url("petition", petition.id),
        content_date=petition.date,
    )


@app.route("/robots.txt", methods=["GET"])
def robots_txt():
    response = make_response(open("robots.txt").read())
    response.headers["Content-type"] = "text/plain"
    return response


@app.route("/parliament-reviews", methods=["GET"])
def parliament_review():
    """
    Show the review articles about parliament
    """
    return render_template("review/landing.html")


@app.route("/parliament-review/article/<article>", methods=["GET"])
def article_review(article):
    article_group = {
        "steven_friedman": "review/articles/2019Review_Steven_Friedman.html",
        "andisiwe_makinana": "review/articles/2019Review_Andisiwe_Makinana.html",
        "law_calland": "review/articles/2019Review_Law_Calland.html",
        "lawson_naidoo": "review/articles/2019Review_Lawson_Naidoo.html",
        "narend_singh": "review/articles/2019Review_Narend_Singh.html",
        "deidre_carter": "review/articles/2019Review_Deidre_Carter.html",
        "gary_pienaar": "review/articles/2019Review_Gary_Pienaar.html",
        "mike_pothier": "review/articles/2019Review_Mike_Pothier.html",
        "duda_motala_louw": "review/articles/2019Review_Duda_Motala_Louw.html",
        "moira_levy": "review/articles/2019Review_Moira_Levy.html",
        "martin_nicol": "review/articles/2019Review_Martin_Nicol.html",
        "judith_febuary": "review/articles/2019Review_Judith_February.html",
        "sean_muller": "review/articles/2019Review_Sean_Muller.html",
        "gaile_fullard": "review/articles/2019Review_Gaile_Fullard.html",
        "monique_doyle": "review/articles/2019Review_Monique_Doyle.html",
    }
    return render_template(article_group[article])


@app.route("/parliament-review/interview/<interview>", methods=["GET"])
def interview_review(interview):
    interview_group = {
        "lechesa_tsenoli": "review/interviews/2019Review_Lechesa_Tsenoli.html",
        "john_steenhuisen": "review/interviews/2019Review_John_Steenhuisen.html",
        "joanmarie_fubbs": "review/interviews/2019Review_Joanmariae_Fubbs.html",
        "mbuyiseni_ndlozi": "review/interviews/2019Review_Mbuyiseni_Ndlozi.html",
        "mp_comments": "review/interviews/2019Review_MP_Comments.html",
        "black_sash": "review/interviews/2019Review_Black_Sash.html",
        "sjc": "review/interviews/2019Review_SJC.html",
        "makhosi_khoza": "review/interviews/2019Review_Makhosi_Khoza.html",
    }
    return render_template(interview_group[interview])


@app.route("/parliament-review/statistics/<stat>", methods=["GET"])
def stats_review(stat):
    stat_group = {
        "turnover": "review/statistics/2019Review_Turnover.html",
        "agenda": "review/statistics/2019Review_Agenda.html",
        "activity": "review/statistics/2019Review_Activity.html",
        "performance": "review/statistics/2019Review_Performance.html",
        "questions": "review/statistics/2019Review_Questions.html",
    }
    return render_template(stat_group[stat])


@app.route("/6th-parliament-review", methods=["GET"])
def pr6():
    return render_template("pr6/landing.html")


@app.route("/6th-parliament-review/<section>/<slug>", methods=["GET"])
def pr6_articles(section, slug):
    return render_template("pr6/article.html", section=section, article=slug)


@app.route("/conference", methods=["GET"])
def conference():
    return render_template("conference/landing.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# Test to make sure sentry is working
@app.route("/debug-sentry")
def trigger_error():
    division_by_zero = 1 // 0
