import logging
from app import db, app
from models import *
import flask
from flask import g, request, abort, redirect, url_for, session, make_response
from functools import wraps
import json
from sqlalchemy import func, or_, distinct, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
import datetime
from operator import itemgetter
import re
import serializers
import sys
from search import Search
import math
from flask_security import current_user

API_HOST = app.config["API_HOST"]

# handling static files (only relevant during development)
app.static_folder = 'static'
app.add_url_rule('/static/<path:filename>',
                 endpoint='static',
                 view_func=app.send_static_file)

logger = logging.getLogger(__name__)


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


def get_filter():
    filters = []
    args = flask.request.args.to_dict()
    for key in args:
        if "filter" in key:
            fieldname = re.search("filter\[(.*)\]", key).group(1)
            if fieldname:
                filters.append({fieldname: args[key]})
    return filters


@app.errorhandler(ApiException)
def handle_api_exception(error):
    """
    Error handler, used by flask to pass the error on to the user, rather than catching it and throwing a HTTP 500.
    """

    response = flask.jsonify(error.to_dict())
    response.status_code = error.status_code
    response.headers['Access-Control-Allow-Origin'] = "*"
    return response


def send_api_response(data_json):

    response = flask.make_response(data_json)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Content-Type'] = "application/json"
    return response


# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if g.user is None or not g.user.is_active():
#             raise ApiException(401, "You need to be logged-in in order to access this resource.")
#         return f(*args, **kwargs)
#     return decorated_function
#
#
# @app.before_request
# def load_user():
#
#     user = None
#     # handle authentication via Auth Header
#     if request.headers.get('Authorization') and request.headers['Authorization'].split(":")[0]=="ApiKey":
#         key_value = request.headers['Authorization'].split(":")[1]
#         api_key = ApiKey.query.filter_by(key=key_value).first()
#         if api_key:
#             user = api_key.user
#     # handle authentication via session cookie (for admin)
#     if session and session.get('api_key'):
#         api_key = ApiKey.query.filter_by(key=session.get('api_key')).first()
#         if api_key:
#             user = api_key.user
#     g.user = user
#     return

# -------------------------------------------------------------------
# API endpoints:
#

def api_resources():
    current_time = datetime.datetime.utcnow()
    return {
        "committee": db.session.query(Committee)
        .order_by(Committee.house_id, Committee.name),

        "committee-meeting": db.session.query(Event)
        .filter(Event.type == 'committee-meeting')
        .order_by(desc(Event.date)),

        "bill": db.session.query(Bill)
        .order_by(desc(Bill.year)),

        "member": db.session.query(Member)
        .order_by(Member.name),

        "hansard": db.session.query(Hansard)
        .order_by(desc(Hansard.meeting_date)),

        "briefing": db.session.query(Briefing)
        .order_by(desc(Briefing.briefing_date)),
        "question_reply": db.session.query(QuestionReply)
        .order_by(desc(QuestionReply.start_date)),
        "schedule": db.session.query(Schedule)
        .order_by(desc(Schedule.meeting_date))
        .filter(Schedule.meeting_date >= current_time),
        "tabled_committee_report": db.session.query(TabledCommitteeReport)
        .order_by(desc(TabledCommitteeReport.start_date)),
        "calls_for_comment": db.session.query(CallForComment)
        .order_by(desc(CallForComment.start_date)),
        "policy_document": db.session.query(PolicyDocument)
        .order_by(desc(PolicyDocument.start_date)),
        "gazette": db.session.query(Gazette)
        .order_by(desc(Gazette.start_date)),
        "book": db.session.query(Book)
        .order_by(desc(Book.start_date)),
        "featured": db.session.query(Featured)
        .order_by(desc(Featured.start_date)),
        "daily_schedule": db.session.query(DailySchedule)
        .order_by(desc(DailySchedule.start_date)),
    }


@app.route('/search/')
def search():
    """
    Search through ElasticSearch
    """

    search = Search()
    filters = {}
    print request.args
    q = request.args.get('q')
    logger.debug("search called")
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
        result["next"] = flask.request.url_root + "search/?q=" + q + \
            "&page=" + str(page + 1) + "&per_page=" + str(per_page)
        result["last"] = flask.request.url_root + "search/?q=" + q + "&page=" + \
            str(int(math.ceil(result["count"] / per_page))) + "&per_page=" + str(per_page)
        result["first"] = flask.request.url_root + "search/?q=" + \
            q + "&page=0" + "&per_page=" + str(per_page)
    return json.dumps(result)


@app.route('/hitlog/', methods=['GET', 'POST'])
def hitlog():
    """
    Records a hit from the end-user. Should be called in a non-blocking manner
    """
    logger.debug("caught a hit")
    hitlog = HitLog(
        ip_addr=flask.request.form["ip_addr"],
        user_agent=flask.request.form["user_agent"],
        url=flask.request.form["url"])
    db.session.add(hitlog)
    db.session.commit()

    return ""


@app.route('/<string:resource>/', )
@app.route('/<string:resource>/<int:resource_id>/', )
def resource_list(resource, resource_id=None):
    """
    Generic resource endpoints.
    """

    base_query = api_resources().get(resource)
    if not base_query:
        raise ApiException(400, "The specified resource type does not exist.")

    # validate paging parameters
    page = 0
    per_page = app.config['RESULTS_PER_PAGE']
    if flask.request.args.get('page'):
        try:
            page = int(flask.request.args.get('page'))
        except ValueError:
            raise ApiException(422, "Please specify a valid 'page'.")
    # if flask.request.args.get('filter'):
    filters = get_filter()
    if (len(filters)):
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
        next = flask.request.url_root + resource + "/?page=" + str(page + 1)
    out = serializers.queryset_to_json(
        queryset,
        count=count,
        next=next,
        current_user=current_user)
    return send_api_response(out)


@app.route('/', )
def landing():
    """
    List available endpoints.
    """

    out = {'endpoints': []}
    for resource in api_resources().keys():
        out['endpoints'].append(API_HOST + resource)
    return send_api_response(json.dumps(out, indent=4))
