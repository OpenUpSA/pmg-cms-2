import logging
from app import db, app
from models import *
import flask
from flask import g, request, abort, redirect, url_for, session, make_response
import json
from sqlalchemy import func, or_, distinct, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
import datetime
from dateutil import tz
from operator import itemgetter
import re
import serializers
import sys
from search import Search
import math
from flask_security import current_user
from flask_security.decorators import load_user
from werkzeug.exceptions import HTTPException

# handling static files (only relevant during development)
app.static_folder = 'static'
app.add_url_rule('/static/<path:filename>',
                 endpoint='static',
                 view_func=app.send_static_file)

logger = logging.getLogger(__name__)


@app.before_request
def before_request():
    if not current_user.is_anonymous():
        # log user's visit, but only once very hour
        now = datetime.datetime.utcnow()
        if current_user.current_login_at + datetime.timedelta(hours=1) < now:
            current_user.current_login_at = now
            db.session.add(current_user)
            db.session.commit()


class ApiException(HTTPException):

    """
    Class for handling all of our expected API errors.
    """

    def __init__(self, status_code, message):
        super(ApiException, self).__init__(message)
        self.code = status_code

    def to_dict(self):
        rv = {
            "code": self.code,
            "message": self.description
        }
        return rv

    def get_response(self, environ=None):
        response = flask.jsonify(self.to_dict())
        response.status_code = self.code
        response.headers['Access-Control-Allow-Origin'] = "*"
        return response


def get_filter():
    filters = []
    args = request.args.to_dict()
    for key in args:
        if "filter" in key:
            fieldname = re.search("filter\[(.*)\]", key).group(1)
            if fieldname:
                filters.append({fieldname: args[key]})
    return filters


def api_resource_list(resource, resource_id, base_query):
    # validate paging parameters
    page = 0
    per_page = app.config['RESULTS_PER_PAGE']
    if request.args.get('page'):
        try:
            page = int(request.args.get('page'))
        except ValueError:
            raise ApiException(422, "Please specify a valid 'page'.")
    filters = get_filter()
    if filters:
        for f in filters:
            base_query = base_query.filter_by(**f)
    if resource_id:
        try:
            queryset = base_query.filter_by(id=resource_id).one()
            count = 1
        except NoResultFound:
            raise ApiException(404, "Not found")
    else:
        queryset = base_query.limit(per_page).offset(page * per_page).all()
        count = base_query.count()
    next = None
    if count > (page + 1) * per_page:
        next = request.url_root + resource + "/?page=" + str(page + 1)
    status_code = 200
    if resource == "committee-meeting" and resource_id:
        committee_meeting_obj = queryset
        if not committee_meeting_obj.check_permission():
            if current_user.is_anonymous():
                status_code = 401  # Unauthorized, i.e. authentication is required
            else:
                status_code = 403  # Forbidden, i.e. the user is not subscribed
    out = serializers.queryset_to_json(
        queryset,
        count=count,
        next=next,
        current_user=current_user)
    return send_api_response(out, status_code=status_code)



def send_api_response(data_json, status_code=200):

    response = flask.make_response(data_json)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Content-Type'] = "application/json"
    response.status_code = status_code
    return response


def api_resources():
    current_time = datetime.datetime.utcnow()
    return {
        "committee": db.session.query(Committee)
        .order_by(Committee.house_id, Committee.name),
        "committee-meeting": db.session.query(CommitteeMeeting)
        .order_by(desc(CommitteeMeeting.date)),
        "bill": db.session.query(Bill)
        .order_by(desc(Bill.year)),
        "member": db.session.query(Member)
        .order_by(Member.name),
        "hansard": db.session.query(Plenary)
        .order_by(desc(Plenary.date)),
        "briefing": db.session.query(Briefing)
        .order_by(desc(Briefing.date)),
        "question_reply": db.session.query(QuestionReply)
        .order_by(desc(QuestionReply.start_date)),
        "schedule": db.session.query(Schedule)
        .order_by(desc(Schedule.meeting_date))
        .filter(Schedule.meeting_date >= current_time),
        "tabled_committee_report": db.session.query(TabledCommitteeReport)
        .order_by(desc(TabledCommitteeReport.start_date)),
        "call_for_comment": db.session.query(CallForComment)
        .order_by(desc(CallForComment.start_date)),
        "policy_document": db.session.query(PolicyDocument)
        .order_by(desc(PolicyDocument.start_date)),
        "gazette": db.session.query(Gazette)
        .order_by(desc(Gazette.start_date)),
        "featured": db.session.query(Featured)
        .order_by(desc(Featured.start_date)),
        "daily_schedule": db.session.query(DailySchedule)
        .order_by(desc(DailySchedule.start_date)),
    }

# -------------------------------------------------------------------
# API endpoints:
#

@app.route('/search/')
def search():
    """
    Search through ElasticSearch
    """

    search = Search()
    filters = {}
    logger.debug("Search args: %s" % request.args)
    q = request.args.get('q')
    page = 0
    if (request.args.get('page')):
        page = int(request.args.get('page'))
    per_page = app.config['RESULTS_PER_PAGE']
    if (request.args.get('per_page')):
        per_page = int(request.args.get('per_page'))
    filters["start_date"] = request.args.get('filter[start_date]')
    filters["end_date"] = request.args.get('filter[end_date]')
    filters["type"] = request.args.get('filter[type]')
    filters["committee"] = request.args.get('filter[committee]')
    searchresult = search.search(
        q,
        per_page,
        page * per_page,
        content_type=filters["type"],
        start_date=filters["start_date"],
        end_date=filters["end_date"],
        committee=filters["committee"])
    bincounts = search.count(q)

    result = {}
    result["result"] = searchresult["hits"]["hits"]
    result["count"] = searchresult["hits"]["total"]
    result["max_score"] = searchresult["hits"]["max_score"]
    result["bincount"] = {}
    result["bincount"]["types"] = bincounts[
        0]["aggregations"]["types"]["buckets"]
    result["bincount"]["years"] = bincounts[
        1]["aggregations"]["years"]["buckets"]
    logger.debug("Pages %i", math.ceil(result["count"] / per_page))

    if result["count"] > (page + 1) * per_page:
        result["next"] = request.url_root + "search/?q=" + q + \
            "&page=" + str(page + 1) + "&per_page=" + str(per_page)
        result["last"] = request.url_root + "search/?q=" + q + "&page=" + \
            str(int(math.ceil(result["count"] / per_page))) + "&per_page=" + str(per_page)
        result["first"] = request.url_root + "search/?q=" + \
            q + "&page=0" + "&per_page=" + str(per_page)
    return json.dumps(result)


@app.route('/hitlog/', methods=['GET', 'POST'])
def hitlog():
    """
    Records a hit from the end-user. Should be called in a non-blocking manner
    """
    logger.debug("caught a hit")
    hitlog = HitLog(
        ip_addr=request.form["ip_addr"],
        user_agent=request.form["user_agent"],
        url=request.form["url"])
    db.session.add(hitlog)
    db.session.commit()

    return ""


@app.route('/bill/<int:bill_id>/')
@app.route('/bill/<string:scope>/')
@load_user('token', 'session')
def current_bill_list(scope=None, bill_id=None):
    if bill_id:
        return api_resource_list('bill', bill_id, api_resources().get('bill'))

    if not scope in ['current', 'draft', 'pmb']:
        raise ApiException(404, "The specified resource group does not exist.")

    query = api_resources().get('bill')

    if scope == 'current':
        statuses = BillStatus.current()
        query = query.filter(Bill.status_id.in_([s.id for s in statuses]))

    elif scope == 'draft':
        query = query.filter(Bill.type == BillType.draft())

    elif scope == 'pmb':
        query = query.filter(Bill.type == BillType.private_member_bill())

    return api_resource_list('bill', None, query)


@app.route('/<string:resource>/', )
@app.route('/<string:resource>/<int:resource_id>/', )
@load_user('token', 'session')
def resource_list(resource, resource_id=None):
    """
    Generic resource endpoints.
    """

    base_query = api_resources().get(resource)
    if not base_query:
        raise ApiException(404, "The specified resource type does not exist.")

    return api_resource_list(resource, resource_id, base_query)


@app.route('/', )
@load_user('token', 'session')
def landing():
    """
    List available endpoints.
    """

    out = {'endpoints': []}
    for resource in api_resources().keys():
        out['endpoints'].append(request.base_url + resource)
    if current_user and current_user.is_active():
        try:
            out['current_user'] = serializers.to_dict(current_user)
        except Exception:
            logger.exception("Error serializing current user.")
            pass
    return send_api_response(json.dumps(out, cls=serializers.CustomEncoder, indent=4))


@app.route('/update_subscriptions/', methods=['POST', ])
@load_user('token')
def update_subscriptions():
    """
    Update user's notification subscriptions.
    """

    out = {}
    if current_user and current_user.is_active():
        committee_subscriptions = request.json.get('committee_subscriptions')
        logger.debug(json.dumps(committee_subscriptions, indent=4))
        general_subscriptions = request.json.get('general_subscriptions')
        logger.debug(json.dumps(general_subscriptions, indent=4))

        # remove user's current subscriptions
        current_user.subscriptions = []
        # retrieve list of chosen committees
        committee_list = Committee.query.filter(Committee.id.in_(committee_subscriptions)).all()
        for committee in committee_list:
            current_user.subscriptions.append(committee)
        # update general True/False subscriptions
        current_user.subscribe_daily_schedule = True if 'daily-schedule' in general_subscriptions else False
        current_user.subscribe_bill = True if 'bill' in general_subscriptions else False
        current_user.subscribe_call_for_comment = True if 'call-for-comment' in general_subscriptions else False
        db.session.add(current_user)
        db.session.commit()
        try:
            out['current_user'] = serializers.to_dict(current_user)
        except Exception:
            logger.exception("Error serializing current user.")
            pass
    return send_api_response(json.dumps(out, indent=4))


@app.route('/check_redirect/', methods=['POST', ])
def check_redirect():
    """
    Check if a given URL should be redirected.
    """

    out = {'redirect': None}
    old_url = request.json.get('url')
    new_url = Redirect.query.filter_by(old_url=old_url).first()
    if new_url:
        out['redirect'] = new_url
    return send_api_response(json.dumps(out, indent=4))
