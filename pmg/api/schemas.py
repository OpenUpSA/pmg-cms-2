from marshmallow import fields
from marshmallow_polyfield import PolyField

from pmg import ma
from pmg.models import (
    Committee,
    House,
    CommitteeMeeting,
    CommitteeMeetingAttendance,
    Member,
    CallForComment,
    TabledCommitteeReport,
    Membership,
    Party,
    CommitteeQuestion,
    File,
    Minister,
    Bill,
    BillType,
    BillVersion,
    BillFile,
    BillStatus,
    Event,
    QuestionReply,
    DailySchedule,
    Petition,
    PetitionEvent,
    PetitionStatus,
)
from pmg.utils import externalise_url


def choose_event_schema(base, parent):
    """ Return the schema to use for Event-based objects.
    """
    name = base.__class__.__name__ + "Schema"
    return globals().get(name, EventSchema)()


class AbsoluteUrlFor(ma.UrlFor):
    """ Customized absolute-ized URL builder to take into account
    the actual requesting host. This ensures requests to api-internal
    use that host in the response.
    """

    def _serialize(self, value, key, obj):
        url = super(AbsoluteUrlFor, self)._serialize(value, key, obj)
        return externalise_url(url)


class CommitteeSchema(ma.ModelSchema):
    class Meta:
        model = Committee
        fields = (
            "id",
            "about",
            "name",
            "house",
            "contact_details",
            "ad_hoc",
            "active",
            "premium",
            "monitored",
            "minister",
            "last_active_year",
            "_links",
        )

    house = fields.Nested("HouseSchema")
    minister = fields.Nested("MinisterSchema", exclude=["committee"])
    _links = ma.Hyperlinks(
        {
            "self": AbsoluteUrlFor("api2.committees", id="<id>"),
            "meetings": AbsoluteUrlFor("api2.committee_meeting_list", id="<id>"),
            "calls_for_comment": AbsoluteUrlFor(
                "api2.committee_calls_for_comment", id="<id>"
            ),
            "tabled_reports": AbsoluteUrlFor(
                "api2.committee_tabled_reports", id="<id>"
            ),
            "members": AbsoluteUrlFor("api2.committee_members", id="<id>"),
        }
    )


class HouseSchema(ma.ModelSchema):
    class Meta:
        model = House
        fields = (
            "id",
            "name",
            "short_name",
            "sphere",
        )

    short_name = fields.String(attribute="name_short")


class EventSchema(ma.ModelSchema):
    class Meta:
        model = Event
        fields = (
            "id",
            "date",
            "title",
            "chairperson",
            "public_participation",
            "committee_id",
            "committee",
            "type",
            "house",
        )

    committee = fields.Nested("CommitteeSchema")
    house = fields.Nested("HouseSchema")


class CommitteeMeetingSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeMeeting
        fields = (
            "id",
            "actual_start_time",
            "actual_end_time",
            "date",
            "title",
            "body",
            "summary",
            "chairperson",
            "public_participation",
            "bills",
            "files",
            "committee_id",
            "_links",
            "committee",
            "premium_content_excluded",
            "premium_but_free",
            "type",
        )

    committee = fields.Nested("CommitteeSchema")
    premium_content_excluded = fields.Method("get_premium_content_excluded")
    body = fields.Method("get_body")
    summary = fields.Method("get_summary")
    files = fields.Nested("FileSchema", attribute="api_files", many=True)
    bills = fields.Nested("BillSchema", many=True, exclude=["events", "versions"])
    _links = ma.Hyperlinks(
        {
            "self": AbsoluteUrlFor("api2.committee_meetings", id="<id>"),
            "committee": AbsoluteUrlFor("api2.committees", id="<committee_id>"),
            "attendance": AbsoluteUrlFor(
                "api2.committee_meeting_attendance", id="<id>"
            ),
        }
    )

    def get_premium_content_excluded(self, obj):
        return not obj.check_permission()

    def get_body(self, obj):
        """ Hide body field for non-premium subscribers
        """
        if obj.check_permission():
            return obj.body
        return None

    def get_summary(self, obj):
        """ Hide summary field for non-premium subscribers
        """
        if obj.check_permission():
            return obj.summary
        return None


class CallForCommentSchema(ma.ModelSchema):
    class Meta:
        model = CallForComment
        fields = (
            "id",
            "title",
            "start_date",
            "end_date",
            "body",
            "summary",
            "committee_id",
            "_links",
            "closed",
            "committee",
        )

    committee = fields.Nested("CommitteeSchema")
    _links = ma.Hyperlinks(
        {
            "self": AbsoluteUrlFor("api2.calls_for_comments", id="<id>"),
            "committee": AbsoluteUrlFor("api2.committees", id="<committee_id>"),
        }
    )


class TabledCommitteeReportSchema(ma.ModelSchema):
    class Meta:
        model = TabledCommitteeReport
        fields = ("id", "title", "start_date", "body", "committee_id", "_links")

    _links = ma.Hyperlinks(
        {
            # 'self': AbsoluteUrlFor('api2.tabled_report', id="<id>"),
            "committee": AbsoluteUrlFor("api2.committees", id="<committee_id>"),
        }
    )


class CommitteeMeetingAttendanceSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeMeetingAttendance
        fields = (
            "id",
            "alternate_member",
            "attendance",
            "chairperson",
            "member",
            "_links",
            "committee_meeting_id",
            "committee_id",
        )

    member = fields.Nested("MemberSchema")
    committee_meeting_id = fields.Number(attribute="meeting_id")
    _links = ma.Hyperlinks(
        {
            "committee": AbsoluteUrlFor("api2.committees", id="<meeting.committee_id>"),
            "committee_meeting": AbsoluteUrlFor(
                "api2.committee_meetings", id="<meeting_id>"
            ),
        }
    )


class MemberSchema(ma.ModelSchema):
    class Meta:
        model = Member
        fields = (
            "id",
            "name",
            "profile_pic_url",
            "party",
            "pa_url",
            "current",
            "house",
        )

    party = fields.Nested("PartySchema")
    house = fields.Nested("HouseSchema")
    pa_url = fields.String(attribute="pa_url")
    profile_pic_url = fields.String(attribute="full_profile_pic_url")


class MembershipSchema(ma.ModelSchema):
    class Meta:
        model = Membership
        fields = ("member", "chairperson")

    member = fields.Nested("MemberSchema")
    chairperson = fields.Boolean(attribute="chairperson")


class PartySchema(ma.ModelSchema):
    class Meta:
        model = Party
        fields = ("id", "name")


class FileSchema(ma.ModelSchema):
    class Meta:
        model = File
        fields = (
            "id",
            "title",
            "description",
            "origname",
            "file_mime",
            "file_bytes",
            "url",
            "file_path",
            "soundcloud_uri",
        )


class MinisterSchema(ma.ModelSchema):
    class Meta:
        model = Minister
        fields = ("id", "name", "_links", "committee")

    committee = fields.Nested("CommitteeSchema", exclude=["minister"])
    # TODO: add link to questions to this minister
    _links = ma.Hyperlinks({"self": AbsoluteUrlFor("api2.ministers", id="<id>"),})


class CommitteeQuestionSchema(ma.ModelSchema):
    class Meta:
        model = CommitteeQuestion
        fields = (
            "id",
            "date",
            "intro",
            "year",
            "code",
            "answer",
            "answer_type",
            "asked_by_member_id",
            "asked_by_name",
            "asked_by_member",
            "question",
            "question_number",
            "question_to_name",
            "created_at",
            "updated_at",
            "written_number",
            "oral_number",
            "president_number",
            "deputy_president_number",
            "house",
            "house_id",
            "minister",
            "minister_id",
            "translated",
            "source_file",
            "files",
            "url",
            "_links",
        )

    asked_by_member = fields.Nested("MemberSchema")
    minister = fields.Nested("MinisterSchema")
    source_file = fields.Nested("FileSchema")
    files = fields.Nested("FileSchema", attribute="api_files", many=True)
    _links = ma.Hyperlinks(
        {"self": AbsoluteUrlFor("api2.minister_questions", id="<id>"),}
    )


class QuestionReplySchema(ma.ModelSchema):
    class Meta:
        model = QuestionReply
        fields = (
            "id",
            "body",
            "title",
            "created_at",
            "updated_at",
            "start_date",
            "question_number",
            "minister",
            "minister_id",
            "_links",
        )

    minister = fields.Nested("MinisterSchema")
    _links = ma.Hyperlinks(
        {"self": AbsoluteUrlFor("api2.minister_questions_legacy", id="<id>"),}
    )


class DailyScheduleSchema(ma.ModelSchema):
    class Meta:
        model = DailySchedule
        fields = (
            "id",
            "body",
            "title",
            "created_at",
            "updated_at",
            "start_date",
            "house",
            "house_id",
            "files",
            "_links",
        )

    house = fields.Nested("HouseSchema")
    files = fields.Nested("FileSchema", attribute="api_files", many=True)
    _links = ma.Hyperlinks({"self": AbsoluteUrlFor("api2.daily_schedules", id="<id>"),})


class BillSchema(ma.ModelSchema):
    class Meta:
        model = Bill
        fields = (
            "id",
            "type",
            "status",
            "code",
            "title",
            "number",
            "year",
            "introduced_by",
            "place_of_introduction",
            "date_of_introduction",
            "date_of_assent",
            "effective_date",
            "act_name",
            "versions",
            "bill_files",
            "events",
            "created_at",
            "updated_at",
        )

    type = fields.Nested("BillTypeSchema")
    status = fields.Nested("BillStatusSchema")
    place_of_introduction = fields.Nested("HouseSchema")
    versions = fields.Nested("BillVersionSchema", many=True)
    bill_files = fields.Nested("BillFileSchema", many=True)
    events = PolyField(serialization_schema_selector=choose_event_schema, many=True)

    _links = ma.Hyperlinks({"self": AbsoluteUrlFor("api2.bills", id="<id>"),})


class BillTypeSchema(ma.ModelSchema):
    class Meta:
        model = BillType
        fields = ("id", "prefix", "description", "name")


class BillStatusSchema(ma.ModelSchema):
    class Meta:
        model = BillStatus
        fields = ("id", "description", "name")


class BillVersionSchema(ma.ModelSchema):
    class Meta:
        model = BillVersion
        fields = ("id", "title", "file", "date", "enacted")

    file = fields.Nested("FileSchema")

class BillFileSchema(ma.ModelSchema):
    class Meta:
        model = BillFile
        fields = ("id", "file_id", "file")

    file = fields.Nested("FileSchema")


class PetitionStatusSchema(ma.ModelSchema):
    class Meta:
        model = PetitionStatus
        fields = ("id", "step", "name", "description")


class PetitionEventSchema(ma.ModelSchema):
    class Meta:
        model = PetitionEvent
        fields = (
            "id",
            "date",
            "title",
            "type",
            "description",
            "status",
            "committee",
            "petition_id",
        )

    status = fields.Nested("PetitionStatusSchema")
    committee = fields.Nested("CommitteeSchema")


class PetitionSchema(ma.ModelSchema):
    class Meta:
        model = Petition
        fields = (
            "id",
            "title",
            "date",
            "house",
            "committees",
            "issue",
            "description",
            "petitioner",
            "petition_file",
            "report",
            "supporting_files",
            "hansard",
            "status",
            "events",
            "created_at",
            "updated_at",
        )

    house = fields.Nested("HouseSchema")
    committees = fields.Nested("CommitteeSchema", many=True)
    petition_file = fields.Nested("FileSchema")
    report = fields.Nested("FileSchema")
    supporting_files = fields.Nested("FileSchema", many=True, attribute="api_files")
    hansard = fields.Nested("EventSchema")
    status = fields.Nested("PetitionStatusSchema")
    events = fields.Nested("PetitionEventSchema", many=True)
