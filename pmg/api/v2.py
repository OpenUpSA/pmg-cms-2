from marshmallow import fields
from flask import request, Blueprint, abort
from sqlalchemy import desc

from pmg import ma
from pmg.models import Committee, House, CommitteeMeeting, CommitteeMeetingAttendance, Member
from pmg.api.v1 import get_filters, paginate_request_query, send_api_response


api = Blueprint('api2', __name__)


class CommitteeSchema(ma.ModelSchema):
    class Meta:
        model = Committee
        fields = ('id', 'about', 'name', 'house', 'contact_details', 'ad_hoc', 'premium',
                  '_links')
    house = fields.Nested('HouseSchema')
    _links = ma.Hyperlinks({
        'self': ma.AbsoluteUrlFor('api2.committees', id="<id>"),
        'meetings': ma.AbsoluteUrlFor('api2.committee_meeting_list', id="<id>"),
        # TODO: memberships, questions, etc.
    })


class HouseSchema(ma.ModelSchema):
    class Meta:
        model = House
        fields = ('id', 'name', 'short_name')
    short_name = fields.String(attribute='name_short')


class CommitteeMeetingSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeMeeting
        fields = ('id', 'actual_start_time', 'actual_end_time', 'date', 'title', 'body', 'summary',
                  'chairperson', 'public_participation', 'bills', 'files', 'committee_id', '_links')
    _links = ma.Hyperlinks({
        'self': ma.AbsoluteUrlFor('api2.committee_meetings', id="<id>"),
        'committee': ma.AbsoluteUrlFor('api2.committees', id="<committee_id>"),
        'attendance': ma.AbsoluteUrlFor('api2.committee_meeting_attendance', id="<id>"),
    })


class CommitteeMeetingAttendanceSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeMeetingAttendance
        fields = ('id', 'alternate_member', 'attendance', 'chairperson', 'member', '_links', 'committee_meeting_id',
                  'committee_id')
    member = fields.Nested('MemberSchema')
    committee_meeting_id = fields.Number(attribute='meeting_id')
    _links = ma.Hyperlinks({
        'committee': ma.AbsoluteUrlFor('api2.committees', id="<meeting.committee_id>"),
        'committee_meeting': ma.AbsoluteUrlFor('api2.committee_meetings', id="<meeting_id>"),
    })


class MemberSchema(ma.ModelSchema):
    class Meta:
        model = Member
        fields = ('id', 'name', 'profile_pic_url', 'party', 'pa_link', 'current')


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
