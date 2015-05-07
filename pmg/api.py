import logging
from functools import wraps
import re
import math

import flask
from flask import request, redirect, url_for, Blueprint
from flask.ext.security import current_user
from flask.ext.security.decorators import _check_token, _check_http_auth
from werkzeug.exceptions import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from pmg import db, app
from pmg.search import Search
from pmg.models import *  # noqa
from pmg.models.base import resource_slugs
import pmg.models.serializers as serializers

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)


def load_user():
    login_mechanisms = {
        'token': lambda: _check_token(),
        'basic': lambda: _check_http_auth(),
        'session': lambda: current_user.is_authenticated()
    }

    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            for mechanism in login_mechanisms.itervalues():
                if mechanism():
                    break
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


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


def get_filters():
    filters = []
    args = request.args.to_dict()

    for key in args:
        if "filter" in key:
            fieldname = re.search("filter\[(.*)\]", key).group(1)
            value = args[key]

            if fieldname:
                if fieldname.endswith('_id'):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                filters.append({fieldname: value})

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

    for f in get_filters():
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
        args = request.args.to_dict()
        args.update(request.view_args)
        args['page'] = page + 1
        # TODO: this isn't great, it allows users to pass in keyword params just by passing
        # in query params
        next = url_for(request.endpoint, _external=True, **args)

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
        next=next)
    return send_api_response(out, status_code=status_code)


def send_api_response(data, status_code=200):
    response = flask.make_response(serializers.to_json(data))
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Content-Type'] = "application/json"
    response.status_code = status_code
    return response


# -------------------------------------------------------------------
# API endpoints:
#

@api.route('/')
def landing():
    """
    List available endpoints.
    """
    endpoints = [request.base_url + s + '/' for s in resource_slugs.iterkeys()]
    return send_api_response({
        'endpoints': endpoints,
        'documentation': 'https://github.com/Code4SA/pmg-cms-2/blob/master/API.md',
    })


@api.route('/admin/')
def old_admin():
    # redirect api.pmg.org.za/admin/ to pmg.org.za/admin/
    return redirect(url_for('admin.index'))


@api.route('/user/')
@load_user()
def user():
    """ Info on the currently logged in user. """
    if current_user.is_anonymous():
        raise ApiException(401, "not authenticated")

    user = serializers.to_dict(current_user)
    user['authentication_token'] = current_user.get_auth_token()

    return send_api_response({'current_user': user})


@api.route('/search/')
def search():
    """
    Search through ElasticSearch
    """
    logger.debug("Search args: %s" % request.args)
    q = request.args.get('q', '').strip()

    try:
        page = int(request.args.get('page', ''))
    except ValueError:
        page = 0

    try:
        per_page = int(request.args.get('per_page', ''))
    except ValueError:
        per_page = app.config['SEARCH_RESULTS_PER_PAGE']

    searchresult = Search().search(
        q,
        per_page,
        page * per_page,
        document_type=request.args.get('type'),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        committee=request.args.get('committee'))

    aggs = searchresult["aggregations"]

    result = {
        "took": searchresult["took"],
        "results": searchresult["hits"]["hits"],
        "page": page,
        "per_page": per_page,
        "pages": int(math.ceil(searchresult["hits"]["total"] / float(per_page))),
        "hits": searchresult["hits"]["total"],
        "max_score": searchresult["hits"]["max_score"],
        "bincount": {
            "types": aggs["types"]["types"]["buckets"],
            "years": aggs["years"]["years"]["buckets"],
        }
    }

    logger.debug("Pages %i", math.ceil(result["hits"] / per_page))

    if result["hits"] > (page + 1) * per_page:
        result["next"] = request.url_root + "search/?q=" + q + \
            "&page=" + str(page + 1) + "&per_page=" + str(per_page)
        result["last"] = request.url_root + "search/?q=" + q + "&page=" + \
            str(int(math.ceil(result["hits"] / per_page))) + "&per_page=" + str(per_page)
        result["first"] = request.url_root + "search/?q=" + \
            q + "&page=0" + "&per_page=" + str(per_page)

    return send_api_response(result)


@api.route('/featured/')
def featured():
    info = {}

    feature = db.session.query(Featured).order_by(desc(Featured.start_date)).first()
    if feature:
        info['feature'] = serializers.to_dict(feature)

    info['committee_meetings'] = CommitteeMeeting.query\
        .filter(CommitteeMeeting.featured == True)\
        .order_by(desc(CommitteeMeeting.date))\
        .all()
    info['committee_meetings'] = [serializers.to_dict(c) for c in info['committee_meetings']]

    return send_api_response(info)


@api.route('/bill/<int:bill_id>/')
@api.route('/bill/<any(current, draft, pmb, tabled):scope>/')
def current_bill_list(scope=None, bill_id=None):
    query = Bill.list()

    if bill_id:
        return api_resource_list('bill', bill_id, query)

    if scope == 'current':
        statuses = BillStatus.current()
        query = query.filter(Bill.status_id.in_([s.id for s in statuses]))

    elif scope == 'draft':
        query = query.filter(Bill.type == BillType.draft())

    elif scope == 'pmb':
        query = query.filter(Bill.type == BillType.private_member_bill())

    elif scope == 'tabled':
        query = query.filter(Bill.type != BillType.draft())

    return api_resource_list('bill', None, query)


@api.route('/committee/premium/')
def committee_list():
    query = Committee.list().filter(Committee.premium == True)  # noqa
    return api_resource_list('committee', None, query)


@api.route('/<string:resource>/', )
@api.route('/<string:resource>/<int:resource_id>/', )
@load_user()
def resource_list(resource, resource_id=None):
    """
    Generic resource endpoints.
    """

    try:
        query = resource_slugs[resource].list()
    except KeyError:
        raise ApiException(404, "The specified resource type does not exist.")

    return api_resource_list(resource, resource_id, query)


@api.route('/committee/question_reply/')
def question_reply_committees():
    """
    A list of those committees that have received questions and replies.
    We might want to generalise this at some point
    """
    items = Committee.for_related(QuestionReply).all()
    return send_api_response(serializers.queryset_to_json(items, count=len(items)))
