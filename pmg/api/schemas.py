from marshmallow import fields

from pmg import ma
from pmg.models import (Committee, House, CommitteeMeeting, CommitteeMeetingAttendance, Member, CallForComment, TabledCommitteeReport,
                        Membership, Party, CommitteeQuestion, File, Minister)


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
        'members': ma.AbsoluteUrlFor('api2.committee_members', id="<id>"),
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
                  'chairperson', 'public_participation', 'bills', 'files', 'committee_id', '_links', 'committee')
    committee = fields.Nested('CommitteeSchema')
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
        fields = ('id', 'name', 'profile_pic_url', 'party', 'pa_url', 'current')
    party = fields.Nested('PartySchema')
    pa_url = fields.String(attribute="pa_url")
    profile_pic_url = fields.String(attribute="full_profile_pic_url")


class MembershipSchema(ma.ModelSchema):
    class Meta:
        model = Membership
        fields = ('member', 'chairperson')
    member = fields.Nested('MemberSchema')
    chairperson = fields.Boolean(attribute="chairperson")


class PartySchema(ma.ModelSchema):
    class Meta:
        model = Party
        fields = ('id', 'name')


class FileSchema(ma.ModelSchema):
    class Meta:
        model = File
        fields = ('id', 'title', 'description', 'origname', 'file_mime', 'file_bytes', 'url', 'file_path')


class MinisterSchema(ma.ModelSchema):
    class Meta:
        model = Minister
        fields = ('id', 'name')
        # TODO: add _links and link to questions to this minister


class CommitteeQuestionSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeQuestion
        fields = ('id', 'date', 'intro', 'year', 'code',
                  'answer', 'answer_type', 'asked_by_member_id', 'asked_by_name', 'asked_by_member',
                  'question', 'question_number', 'question_to_name',
                  'committee_id', 'committee',
                  'created_at', 'updated_at',
                  'written_number', 'oral_number', 'president_number', 'deputy_president_number',
                  'house', 'house_id', 'minister', 'minister_id',
                  'translated', 'source_file', 'url', '_links',)
    committee = fields.Nested('CommitteeSchema')
    asked_by_member = fields.Nested('MemberSchema')
    minister = fields.Nested('MinisterSchema')
    source_file = fields.Nested('FileSchema')
    _links = ma.Hyperlinks({
        'self': ma.AbsoluteUrlFor('api2.minister_questions', id="<id>"),
    })
