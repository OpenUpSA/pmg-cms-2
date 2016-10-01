from marshmallow import fields

from pmg import ma
from pmg.models import Committee, House, CommitteeMeeting, CommitteeMeetingAttendance, Member, CallForComment, TabledCommitteeReport


class CommitteeSchema(ma.ModelSchema):
    class Meta:
        model = Committee
        fields = ('id', 'about', 'name', 'house', 'contact_details', 'ad_hoc', 'premium',
                  '_links')
    house = fields.Nested('HouseSchema')
    _links = ma.Hyperlinks({
        'self': ma.AbsoluteUrlFor('api2.committees', id="<id>"),
        'meetings': ma.AbsoluteUrlFor('api2.committee_meeting_list', id="<id>"),
        'calls_for_comment': ma.AbsoluteUrlFor('api2.committee_calls_for_comment', id="<id>"),
        'tabled_reports': ma.AbsoluteUrlFor('api2.committee_tabled_reports', id="<id>"),
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


class CallForCommentSchema(ma.ModelSchema):
    class Meta:
        model = CallForComment
        fields = ('id', 'title', 'start_date', 'end_date', 'body', 'summary', 'committee_id', '_links')
    _links = ma.Hyperlinks({
        # 'self': ma.AbsoluteUrlFor('api2.call_for_comment', id="<id>"),
        'committee': ma.AbsoluteUrlFor('api2.committees', id="<committee_id>"),
    })


class TabledCommitteeReportSchema(ma.ModelSchema):
    class Meta:
        model = TabledCommitteeReport
        fields = ('id', 'title', 'start_date', 'body', 'committee_id', '_links')
    _links = ma.Hyperlinks({
        # 'self': ma.AbsoluteUrlFor('api2.tabled_report', id="<id>"),
        'committee': ma.AbsoluteUrlFor('api2.committees', id="<committee_id>"),
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
