from marshmallow import fields
from flask import request, Blueprint, abort
from sqlalchemy import desc

from pmg import ma
from pmg.models import Committee, House, CommitteeMeeting, CommitteeMeetingAttendance, Member
from pmg.api import get_filters, paginate_request_query, send_api_response


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


@api.route('/committees/')
@api.route('/committees/<int:id>')
def committees(id=None):
    fields = request.args.get('fields') or ''
    fields = [f for f in fields.split(',') if f]
    if not fields:
        fields = None

    if id:
        item = Committee.query.get(id)
        if not item:
            abort(404)

        item, errors = CommitteeSchema(only=fields).dump(item)

        out = {'result': item}

    else:
        base_query = Committee.list()
        for f in get_filters():
            base_query = base_query.filter_by(**f)

        queryset, count, next = paginate_request_query(base_query)

        results, errors = CommitteeSchema(many=True, only=fields).dump(queryset)

        out = {
            'count': count,
            'next': next,
            'results': results
        }

    return send_api_response(out)


@api.route('/committees/<int:id>/meetings')
def committee_meeting_list(id):
    # TODO: fields, paginate, etc.

    cte = Committee.query.get(id)
    if not cte:
        abort(404)

    base_query = CommitteeMeeting.query.filter(CommitteeMeeting.committee_id == id).order_by(desc(CommitteeMeeting.date))
    for f in get_filters():
        base_query = base_query.filter_by(**f)

    queryset, count, next = paginate_request_query(base_query)

    results, errors = CommitteeMeetingSchema(many=True).dump(queryset)

    out = {
        'count': count,
        'next': next,
        'results': results
    }

    return send_api_response(out)


@api.route('/committee-meetings/')
@api.route('/committee-meetings/<int:id>')
def committee_meetings(id=None):
    # TODO: fields, paginate, etc.

    if id:
        item = CommitteeMeeting.query.filter(CommitteeMeeting.id == id).first()
        if not item:
            abort(404)

        item, errors = CommitteeMeetingSchema().dump(item)
        out = {'result': item}

    else:
        base_query = CommitteeMeeting.query.filter(CommitteeMeeting.committee_id == id).order_by(desc(CommitteeMeeting.date))
        for f in get_filters():
            base_query = base_query.filter_by(**f)

        queryset, count, next = paginate_request_query(base_query)

        results, errors = CommitteeMeetingSchema(many=True).dump(queryset)

        out = {
            'count': count,
            'next': next,
            'results': results
        }

    return send_api_response(out)


@api.route('/committee-meetings/<int:id>/attendance')
def committee_meeting_attendance(id):
    # TODO: fields, paginate, etc.
    item = CommitteeMeeting.query.filter(CommitteeMeeting.id == id).first()
    if not item:
        abort(404)

    base_query = CommitteeMeetingAttendance.query.filter(CommitteeMeetingAttendance.meeting_id == id)
    for f in get_filters():
        base_query = base_query.filter_by(**f)

    queryset, count, next = paginate_request_query(base_query)

    results, errors = CommitteeMeetingAttendanceSchema(many=True).dump(queryset)

    out = {
        'count': count,
        'next': next,
        'results': results
    }

    return send_api_response(out)
