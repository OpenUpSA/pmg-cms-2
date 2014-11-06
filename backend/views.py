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
from search.search import Search
import math

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

api_resources = {
    "committee": db.session.query(Organisation) \
        .filter_by(type='committee') \
        .order_by(Organisation.house_id, Organisation.name),
    "committee-meeting": db.session.query(Event) \
        .filter(EventType.name=='committee-meeting') \
        .order_by(desc(Event.date)),

    "bill": db.session.query(Bill)
        .order_by(desc(Bill.effective_date)),

    "member": db.session.query(Member)
        .order_by(Member.name),

    "hansard": db.session.query(Hansard)
        .order_by(Hansard.meeting_date),
    }

@app.route('/search/')
def search():
    """
    Search through ElasticSearch
    """
    
    search = Search()
    q = request.args.get('q')
    logger.debug("search called")
    page = 0
    if (request.args.get('page')):
        page = int(request.args.get('page'))
    per_page = app.config['RESULTS_PER_PAGE']
    if (request.args.get('per_page')):
        per_page = int(request.args.get('per_page'))
    searchresult = search.search(q, per_page, page * per_page)
    result = {}
    result["result"] = searchresult["hits"]["hits"]
    result["count"] = searchresult["hits"]["total"]
    result["max_score"] = searchresult["hits"]["max_score"]
    logger.debug("Pages %i", math.ceil(result["count"] / per_page))
    
    if result["count"] > (page + 1) * per_page:
        result["next"] = flask.request.url_root + "search/?q=" + q + "&page=" + str(page+1) + "&per_page=" + str(per_page)
        result["last"] = flask.request.url_root + "search/?q=" + q + "&page=" + str(int(math.ceil(result["count"] / per_page))) + "&per_page=" + str(per_page)
        result["first"] = flask.request.url_root + "search/?q=" + q + "&page=0" + "&per_page=" + str(per_page)
    return json.dumps(result)

@app.route('/<string:resource>/', )
@app.route('/<string:resource>/<int:resource_id>/', )
def resource_list(resource, resource_id=None):
    """
    Generic resource endpoints.
    """

    if not api_resources.get(resource):
        raise ApiException(400, "The specified resource type does not exist.")

    # validate paging parameters
    page = 0
    per_page = app.config['RESULTS_PER_PAGE']
    if flask.request.args.get('page'):
        try:
            page = int(flask.request.args.get('page'))
        except ValueError:
            raise ApiException(422, "Please specify a valid 'page'.")

    base_query = api_resources[resource]
    if resource_id:
        try:
            queryset = base_query.filter_by(id=resource_id).one()
        except NoResultFound:
            raise ApiException(404, "Not found")
    else:
        queryset = base_query.limit(per_page).offset(page*per_page).all()

    count = base_query.count()
    next = None
    if count > (page + 1) * per_page:
        next = flask.request.url_root + resource + "/?page=" + str(page+1)
    out = serializers.queryset_to_json(queryset, count=count, next=next)
    return send_api_response(out)


@app.route('/', )
def landing():
    """
    List available endpoints.
    """

    out = {'endpoints': []}
    for resource in api_resources.keys():
        out['endpoints'].append(API_HOST + resource)
    return send_api_response(json.dumps(out, indent=4))
