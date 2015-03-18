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
        args['page'] = page+1
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
            .options(joinedload('house'),
                     joinedload('province'),
                     joinedload('memberships.committee'))
            .filter(Member.current == True)
            .order_by(Member.name),
        "hansard": db.session.query(Hansard)
            .order_by(desc(Hansard.date)),
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
        "daily_schedule": db.session.query(DailySchedule)
            .order_by(desc(DailySchedule.start_date)),
    }

# -------------------------------------------------------------------
# API endpoints:
#

@app.route('/user/')
@load_user('token', 'session')
def user():
    """ Info on the currently logged in user. """
    if current_user.is_anonymous():
        raise ApiException(401, "not authenticated")

    current_user.update_current_login()
    return send_api_response({'current_user': serializers.to_dict(current_user)})


@app.route('/search/')
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

@app.route('/featured/')
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


@app.route('/bill/<int:bill_id>/')
@app.route('/bill/<any(current, draft, pmb, tabled):scope>/')
@load_user('token', 'session')
def current_bill_list(scope=None, bill_id=None):
    if bill_id:
        return api_resource_list('bill', bill_id, api_resources().get('bill'))

    query = api_resources().get('bill')

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

@app.route('/committee/premium/')
@load_user('token', 'session')
def committee_list():
    query = api_resources().get('committee').filter(Committee.premium == True)
    return api_resource_list('committee', None, query)


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

@app.route('/committee/question_reply/')
def question_reply_committees():
    """
    A list of those committees that have received questions and replies.
    We might want to generalise this at some point
    """
    items = Committee.for_related(QuestionReply).all()
    return send_api_response(serializers.queryset_to_json(items, count=len(items)))


@app.route('/', )
@load_user('token', 'session')
def landing():
    """
    List available endpoints.
    """

    out = {'endpoints': []}
    for resource in api_resources().keys():
        out['endpoints'].append(request.base_url + resource)
    return send_api_response(out)


@app.route('/update_alerts/', methods=['POST', ])
@load_user('token')
def update_alerts():
    """
    Update user's notification alerts.
    """

    out = {}
    if current_user and current_user.is_active():
        committee_alerts = request.json.get('committee_alerts')
        logger.debug(json.dumps(committee_alerts, indent=4))

        general_alerts = request.json.get('general_alerts')
        logger.debug(json.dumps(general_alerts, indent=4))

        # remove user's current subscriptions
        current_user.committee_alerts = Committee.query.filter(Committee.id.in_(committee_alerts)).all()

        # update general True/False subscriptions
        current_user.subscribe_daily_schedule = True if 'daily-schedule' in general_alerts else False
        db.session.add(current_user)
        db.session.commit()
        try:
            out['current_user'] = serializers.to_dict(current_user)
        except Exception:
            logger.exception("Error serializing current user.")
            pass
    return send_api_response(out)


@app.route('/check_redirect/', methods=['POST', ])
def check_redirect():
    """
    Check if a given URL should be redirected.
    """

    out = {'redirect': None}
    old_url = request.json.get('url')
    if old_url.endswith("/"):
        old_url = old_url[0:-1]
    redirect_obj = Redirect.query.filter_by(old_url=old_url).first()

    if redirect_obj:
        if redirect_obj.new_url:
            out['redirect'] = redirect_obj.new_url
            if not out['redirect'].startswith('/'):
                out['redirect'] = "/" + out['redirect']
        elif redirect_obj.nid:
            # look for 'event' table record with this nid
            committee_meeting = CommitteeMeeting.query.filter_by(nid=redirect_obj.nid).first()
            if committee_meeting:
                out['redirect'] = '/committee-meeting/' + str(committee_meeting.id) + '/'
            else:
                briefing = Briefing.query.filter_by(nid=redirect_obj.nid).first()
                if briefing:
                    out['redirect'] = '/briefing/' + str(briefing.id) + '/'
                else:
                    hansard = Hansard.query.filter_by(nid=redirect_obj.nid).first()
                    if hansard:
                        out['redirect'] = '/hansard/' + str(hansard.id) + '/'
            # look for other non-event records
            if out['redirect'] is None:
                question_reply = QuestionReply.query.filter_by(nid=redirect_obj.nid).first()
                if question_reply:
                    out['redirect'] = '/question_reply/' + str(question_reply.id) + '/'
            if out['redirect'] is None:
                call_for_comment = CallForComment.query.filter_by(nid=redirect_obj.nid).first()
                if call_for_comment:
                    out['redirect'] = '/call-for-comment/' + str(call_for_comment.id) + '/'
            if out['redirect'] is None:
                policy_doc = PolicyDocument.query.filter_by(nid=redirect_obj.nid).first()
                if policy_doc:
                    out['redirect'] = '/policy-document/' + str(policy_doc.id) + '/'
            if out['redirect'] is None:
                gazette = Gazette.query.filter_by(nid=redirect_obj.nid).first()
                if gazette:
                    out['redirect'] = '/gazette/' + str(gazette.id) + '/'
            if out['redirect'] is None:
                daily_schedule = DailySchedule.query.filter_by(nid=redirect_obj.nid).first()
                if daily_schedule:
                    out['redirect'] = '/daily-schedule/' + str(daily_schedule.id) + '/'

    return send_api_response(out)


@app.route('/page/')
def page():
    slug = request.args.get('slug', '').strip()
    if not slug:
        raise ApiException(404, "No such page")

    slug = Page().validate_slug(None, slug)

    page = Page.query.filter(Page.slug == slug).first()
    if not page:
        raise ApiException(404, "No such page")

    return send_api_response(serializers.queryset_to_json(page))
