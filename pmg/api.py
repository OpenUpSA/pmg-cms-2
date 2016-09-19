import logging
from functools import wraps
from itertools import groupby
import re
import math

import flask
from flask import request, redirect, url_for, Blueprint, make_response
from flask.ext.security import current_user
from flask.ext.security.decorators import _check_token, _check_http_auth
from werkzeug.exceptions import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import lazyload, joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import literal_column
from marshmallow import fields

from pmg import db, app
from pmg.search import Search
from pmg.models import *  # noqa
from pmg.models.base import resource_slugs
from pmg.admin.xlsx import XLSXBuilder
import pmg.models.serializers as serializers

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

# This is a temporary fix to only show attendance for members
# of the three major parties until we determine how to present
# faulty passed records for alternate members
MAJOR_PARTIES = ['ANC', 'DA', 'EFF']

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


def api_resource(resource_id, base_query):
    try:
        resource = base_query.filter_by(id=resource_id).one()
    except NoResultFound:
        raise ApiException(404, "Not found")

    status_code = 200
    if resource == "committee-meeting":
        if not resource.check_permission():
            if current_user.is_anonymous():
                status_code = 401  # Unauthorized, i.e. authentication is required
            else:
                status_code = 403  # Forbidden, i.e. the user is not subscribed

    return send_api_response(serializers.queryset_to_json(resource), status_code=status_code)


def paginate_request_query(base_query):
    per_page = app.config['RESULTS_PER_PAGE']
    try:
        per_page = max(min(per_page, int(request.args.get('per_page', per_page))), 1)
    except ValueError:
        pass

    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        raise ApiException(422, "Please specify a valid 'page'.")

    query = base_query.limit(per_page).offset(page * per_page).all()
    count = base_query.count()
    next = create_next_page_url(count, page, per_page)

    return query, count, next


def create_next_page_url(count, page, per_page):
    """
    Generate the next page URL for the current request and
    the provided page params.
    """
    if count > (page + 1) * per_page:
        args = request.args.to_dict()
        args.update(request.view_args)
        args['page'] = page + 1
        # TODO: this isn't great, it allows users to pass in keyword params just by passing
        # in query params
        return url_for(request.endpoint, _external=True, **args)

    return None


def api_resource_list(base_query):
    for f in get_filters():
        base_query = base_query.filter_by(**f)

    queryset, count, next = paginate_request_query(base_query)

    out = serializers.queryset_to_json(queryset, count=count, next=next)
    return send_api_response(out)


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

    try:
        searchresult = Search().search(
            q,
            per_page,
            page * per_page,
            document_type=request.args.get('type'),
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            committee=request.args.get('committee'))
    except ValueError:
        # no query passed in
        raise ApiException(422, "No search term given.")

    aggs = searchresult["aggregations"]

    # ensure all results have a highlight field
    for result in searchresult['hits']['hits']:
        result.setdefault('highlight', {})

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

    committee_meetings = CommitteeMeeting.query\
        .filter(CommitteeMeeting.featured == True)\
        .order_by(desc(CommitteeMeeting.date))\
        .all()  # noqa
    pages = Page.query\
        .filter(Page.featured == True)\
        .order_by(desc(Page.updated_at))\
        .all()  # noqa
    info['committee_meetings'] = [serializers.to_dict(c) for c in committee_meetings]
    info['pages'] = [serializers.to_dict(c) for c in pages]
    return send_api_response(info)


@api.route('/bill/<int:bill_id>/')
@api.route('/bill/<any(current, draft, pmb, tabled):scope>/')
def current_bill_list(scope=None, bill_id=None):
    query = Bill.list()

    if bill_id:
        return api_resource(bill_id, query)

    if scope == 'current':
        statuses = BillStatus.current()
        query = query.filter(Bill.status_id.in_([s.id for s in statuses]))

    elif scope == 'draft':
        query = query.filter(Bill.type == BillType.draft())

    elif scope == 'pmb':
        query = query.filter(Bill.type == BillType.private_member_bill())

    elif scope == 'tabled':
        query = query.filter(Bill.type != BillType.draft())

    return api_resource_list(query)


@api.route('/committee/premium/')
def committee_list():
    query = Committee.list().filter(Committee.premium == True)  # noqa
    return api_resource_list(query)


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
        raise ApiException(404, "The resource type '%s' does not exist." % resource)

    if resource_id:
        return api_resource(resource_id, query)
    else:
        return api_resource_list(query)


@api.route('/member/<int:member_id>/questions/')
def member_questions(member_id):
    """
    Questions asked by this member
    """
    # don't eager load duplicate committee details
    query = CommitteeQuestion.list()\
        .filter(CommitteeQuestion.asked_by_member_id == member_id)\
        .options(joinedload('asked_by_member'))

    return api_resource_list(query)


@api.route('/member/<int:member_id>/attendance/')
def member_attendance(member_id):
    """
    MP attendance of committee meetings.
    """
    query = CommitteeMeetingAttendance.list()\
        .filter(CommitteeMeetingAttendance.member_id == member_id)\
        .options(lazyload('member'), joinedload('meeting'))

    return api_resource_list(query)


@api.route('/committee/question_reply/')
def question_reply_committees():
    """
    A list of those committees that have received questions and replies.
    We might want to generalise this at some point
    """
    items = Committee.for_related(QuestionReply).all()
    return send_api_response(serializers.queryset_to_json(items, count=len(items)))


@api.route('/minister-questions-combined/')
def minister_questions_combined():
    """
    Mixture of old QuestionReplies and new CommitteeQuestion objects
    folded together in date order to support pagination.
    """
    filters = get_filters()

    # To make pagination possible, we grab a combined list of IDs,
    # paginate that list, and then fetch the details.

    # get a combined list of IDs
    q1 = db.session.query(CommitteeQuestion.id, CommitteeQuestion.date.label("date"), literal_column("'cq'").label("type"))
    for f in filters:
        q1 = q1.filter_by(**f)

    q2 = db.session.query(QuestionReply.id, QuestionReply.start_date.label("date"), literal_column("'qr'").label("type"))
    for f in filters:
        q2 = q2.filter_by(**f)

    query = q1.union_all(q2).order_by(desc("date"))
    query, count, next = paginate_request_query(query)

    # pull out the IDs we want
    cq_ids = [c[0] for c in query if c[2] == 'cq']
    qr_ids = [c[0] for c in query if c[2] == 'qr']

    # get committee questions
    query = CommitteeQuestion.list()\
        .filter(CommitteeQuestion.id.in_(cq_ids))\
        .order_by(CommitteeQuestion.date.desc())\
        .options(
            lazyload('committee'),
            lazyload('minister'),
            joinedload('asked_by_member'),
            lazyload('asked_by_member.memberships'))
    for f in filters:
        query = query.filter_by(**f)
    objects = query.all()

    # get question reply objects
    query = QuestionReply.list()\
        .filter(QuestionReply.id.in_(qr_ids))\
        .order_by(QuestionReply.start_date.desc())\
        .options(
            lazyload('committee'),
            lazyload('minister'))
    for f in filters:
        query = query.filter_by(**f)
    # mash them together
    objects.extend(query.all())

    # sort
    objects.sort(key=lambda x: getattr(x, 'date', getattr(x, 'start_date', None)), reverse=True)

    out = serializers.queryset_to_json(objects, count=count, next=next)
    return send_api_response(out)


@api.route('/minister/<int:minister_id>/questions/')
def minister_questions(minister_id):
    """
    Questions asked to a minister
    """
    # don't eager load duplicate committee details
    query = CommitteeQuestion.list()\
        .filter(CommitteeQuestion.minister_id == minister_id)\
        .order_by(CommitteeQuestion.date.desc())\
        .options(
            lazyload('committee'),
            lazyload('minister'),
            joinedload('asked_by_member'),
            lazyload('asked_by_member.memberships'))

    return api_resource_list(query)


@api.route('/committee/<int:committee_id>/questions/')
def committee_questions(committee_id):
    """
    Questions asked to the minister of a committee.
    """
    # don't eager load duplicate committee details
    query = CommitteeQuestion.list()\
        .filter(CommitteeQuestion.committee_id == committee_id)\
        .options(lazyload('committee'))\
        .options(joinedload('asked_by_member'))

    return api_resource_list(query)


@api.route('/committee-meeting/<int:committee_meeting_id>/attendance/')
def committee_meeting_attendance(committee_meeting_id):
    """
    MP attendance of committee meetings.
    """
    query = CommitteeMeetingAttendance.list()\
        .filter(CommitteeMeetingAttendance.meeting_id == committee_meeting_id)\
        .options(lazyload('member.memberships'))

    return api_resource_list(query)


@api.route('/committee-meeting-attendance/summary/')
def committee_meeting_attendance_summary():
    """
    Summary of MP attendance of committee meetings.
    """
    # This is a temporary fix to only show attendance for members
    # of the three major parties until we determine how to present
    # faulty passed records for alternate members

    rows = CommitteeMeetingAttendance.summary()
    members = Member.query\
        .options(joinedload('house'),
                 lazyload('memberships'))\
        .join(Member.party)\
        .filter(Party.name.in_(MAJOR_PARTIES))\
        .all()

    members = {m.id: m for m in members}

    data = []
    for year, year_rows in groupby(rows, lambda r: int(r.year)):
        summaries = []

        for member_id, member_rows in groupby(year_rows, lambda r: r.member_id):
            m = members.get(member_id, None)
            if m:
                member = {'id': member_id}
                member['name'] = m.name
                member['party_id'] = m.party.id if m.party else None
                member['party_name'] = m.party.name if m.party else None
                member['pa_url'] = m.pa_url

                summaries.append({
                    'member': member,
                    'attendance': {row.attendance: row.cnt for row in member_rows},
                })

        data.append({
            'start_date': '%d-01-01' % year,
            'end_date': '%d-12-31' % year,
            'attendance_summary': summaries,
        })

    return send_api_response({'results': data})


@api.route('/committee-meeting-attendance/data.xlsx')
def committee_meeting_attendance_download():
    """
    Download committee meeting attendance data in raw form.
    """
    builder = XLSXBuilder()
    output, wb = builder.new_workbook()

    # attendance summary, by MP

    # This is a temporary fix to only show attendance for members
    # of the three major parties until we determine how to present
    # faulty passed records for alternate members
    members = {m.id: m for m in Member.query.join(Member.party).filter(Party.name.in_(MAJOR_PARTIES)).all()}
    keys = sorted(CommitteeMeetingAttendance.ATTENDANCE_CODES.keys())
    rows = [["year", "member", "party"] + [CommitteeMeetingAttendance.ATTENDANCE_CODES[k] for k in keys]]

    raw_data = CommitteeMeetingAttendance.summary()

    for grp, group in groupby(raw_data, lambda r: [r.year, r.member_id]):
        year, member_id = grp
        member = members.get(member_id, None)
        # This check can be removed once we return all party members
        if member:
            party = member.party.name if member.party else None
            attendance = {r.attendance: r.cnt for r in group}

            row = [year, member.name, party]
            row.extend(attendance.get(k, 0) for k in keys)
            rows.append(row)

    ws = wb.add_worksheet('summary')
    builder.write_table(ws, rows)

    # all done
    wb.close()
    output.seek(0)

    xlsx = output.read()

    resp = make_response(xlsx)
    resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    resp.headers['Content-Disposition'] = "attachment;filename=committee-attendance.xlsx"
    return resp


from pmg import ma


class CommitteeSchema(ma.ModelSchema):
    class Meta:
        model = Committee
        fields = ('id', 'about', 'name', 'house', '_links')
    house = fields.Nested('HouseSchema')
    _links = ma.Hyperlinks({
        'events': ma.AbsoluteUrlFor('api.resource_list', resource='committee-meeting'),
    })


class HouseSchema(ma.ModelSchema):
    class Meta:
        model = House
        fields = ('id', 'name')


@api.route('/v2/committees')
def api_v2_committees():
    base_query = Committee.list()
    for f in get_filters():
        base_query = base_query.filter_by(**f)

    queryset, count, next = paginate_request_query(base_query)

    fields = request.args.get('fields') or ''
    fields = [f for f in fields.split(',') if f]
    if not fields:
        fields = None

    results = CommitteeSchema(many=True, only=fields).dump(queryset)

    out = {
        'count': count,
        'next': next,
        'results': results
    }

    return send_api_response(out)
