from flask import request, Blueprint, abort
from sqlalchemy import desc
from sqlalchemy.sql.expression import nullslast

from pmg.models import Committee, CommitteeMeeting, CommitteeMeetingAttendance, CallForComment
from pmg.api.v1 import get_filters, paginate_request_query, send_api_response
from pmg.api.schemas import *  # noqa


api = Blueprint('api2', __name__)


def get_api_fields():
    fields = request.args.get('fields') or ''
    fields = [f for f in fields.split(',') if f]
    if not fields:
        fields = None
    return fields


def apply_filters(query):
    for f in get_filters():
        query = query.filter_by(**f)
    return query


def api_list_items(query, schema):
    query = apply_filters(query)
    queryset, count, next = paginate_request_query(query)
    results, errors = schema(many=True, only=get_api_fields()).dump(queryset)
    out = {
        'count': count,
        'next': next,
        'results': results
    }
    return send_api_response(out)


def api_get_item(id, model, schema):
    item = model.query.get(id)
    if not item:
        abort(404)

    item, errors = schema(only=get_api_fields()).dump(item)
    return send_api_response({'result': item})


@api.route('/committees/')
@api.route('/committees/<int:id>')
def committees(id=None):
    if id:
        return api_get_item(id, Committee, CommitteeSchema)
    else:
        return api_list_items(Committee.list(), CommitteeSchema)


@api.route('/committees/<int:id>/meetings')
def committee_meeting_list(id):
    cte = Committee.query.get(id)
    if not cte:
        abort(404)

    query = CommitteeMeeting.query.filter(CommitteeMeeting.committee == cte).order_by(desc(CommitteeMeeting.date))
    return api_list_items(query, CommitteeMeetingSchema)


@api.route('/committees/<int:id>/calls-for-comment')
def committee_calls_for_comment(id):
    cte = Committee.query.get(id)
    if not cte:
        abort(404)

    query = CallForComment.query.filter(CallForComment.committee == cte).order_by(desc(CallForComment.start_date))
    return api_list_items(query, CallForCommentSchema)


@api.route('/committees/<int:id>/tabled-reports')
def committee_tabled_reports(id):
    cte = Committee.query.get(id)
    if not cte:
        abort(404)

    query = TabledCommitteeReport.query\
        .filter(TabledCommitteeReport.committee == cte)\
        .order_by(nullslast(desc(TabledCommitteeReport.start_date)))
    return api_list_items(query, TabledCommitteeReportSchema)


@api.route('/committees/<int:id>/members')
def committee_members(id):
    cte = Committee.query.get(id)
    if not cte:
        abort(404)

    query = Membership.query.filter(Membership.committee == cte)
    return api_list_items(query, MembershipSchema)


@api.route('/committee-meetings/')
@api.route('/committee-meetings/<int:id>')
def committee_meetings(id=None):
    if id:
        return api_get_item(id, CommitteeMeeting, CommitteeMeetingSchema)
    else:
        return api_list_items(CommitteeMeeting.list(), CommitteeMeetingSchema)


@api.route('/committee-meetings/<int:id>/attendance')
def committee_meeting_attendance(id):
    item = CommitteeMeeting.query.filter(CommitteeMeeting.id == id).first()
    if not item:
        abort(404)

    query = CommitteeMeetingAttendance.query.filter(CommitteeMeetingAttendance.meeting == item)
    return api_list_items(query, CommitteeMeetingAttendanceSchema)


@api.route('/minister-questions/')
@api.route('/minister-questions/<int:id>')
def minister_questions(id=None):
    if id:
        return api_get_item(id, CommitteeQuestion, CommitteeQuestionSchema)
    else:
        return api_list_items(CommitteeQuestion.list(), CommitteeQuestionSchema)


@api.route('/members/')
@api.route('/members/<int:id>')
def members(id=None):
    if id:
        return api_get_item(id, Member, MemberSchema)
    else:
        return api_list_items(Member.list(), MemberSchema)


@api.route('/calls-for-comments/')
@api.route('/calls-for-comments/<int:id>')
def calls_for_comments(id=None):
    if id:
        return api_get_item(id, CallForComment, CallForCommentSchema)
    else:
        return api_list_items(CallForComment.list(), CallForCommentSchema)
