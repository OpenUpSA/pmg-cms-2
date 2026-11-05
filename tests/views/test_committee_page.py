import datetime

from tests import PMGLiveServerTestCase
from pmg.models import db, Committee, CommitteeQuestion, Minister
from tests.fixtures import (
    dbfixture,
    HouseData,
    MinisterData,
    CommitteeData,
    CommitteeMeetingData,
    CallForCommentData,
    TabledCommitteeReportData,
    CommitteeQuestionData,
    EventData,
    BillData,
    CommitteeMeetingAttendanceData,
)


class TestCommitteePage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteePage, self).setUp()

        self.fx = dbfixture.data(
            HouseData,
            CommitteeData,
            CommitteeMeetingData,
            CallForCommentData,
            TabledCommitteeReportData,
            CommitteeQuestionData,
            BillData,
            EventData,
            CommitteeMeetingAttendanceData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteePage, self).tearDown()

    def test_committee_page(self):
        """
        Test committee page (/committee/<id>/)
        """
        committee = self.fx.CommitteeData.arts
        self.make_request("/committee/%s/" % committee.id)
        self.assertIn(committee.name, self.html)
        self.containsCommitteeMeetings()
        self.containsCallsForComments()
        self.containsTabledReports()
        self.containsQuestionsAndReplies()
        self.containsBills()
        self.containsAttendance()

    def test_committee_page_write_to_committee_facet(self):
        """
        Test the presence of the "Write to committee" facet on the 
        committee page (/committee/<id>/)
        """
        for committee_tuple in self.fx.CommitteeData:
            committee = committee_tuple[1]
            self.make_request("/committee/%s/" % committee.id)
            if committee.active and committee.house.name_short == "NA":
                self.assertIn("Write to this committee", self.html)
            else:
                self.assertNotIn("Write to this committee", self.html)

    def test_committee_page_additional_ministers(self):
        """
        Questions to a committee's additional ministers are shown alongside
        those to its main minister.
        """
        committee = Committee.query.get(self.fx.CommitteeData.arts.id)
        president = Minister.query.get(MinisterData.president.id)
        committee.additional_ministers.append(president)
        question = CommitteeQuestion(
            minister=president,
            house_id=self.fx.HouseData.na.id,
            code="NA99",
            question_number=99,
            written_number=99,
            answer_type="written",
            date=datetime.date(2019, 2, 1),
            year=2019,
            question="A question to the President about the Presidency",
            answer="An answer",
            asked_by_name="Questioner, Mr Q",
        )
        db.session.add(question)
        db.session.commit()

        try:
            self.make_request("/committee/%s/" % committee.id)
            self.assertIn("NA99 by Questioner, Mr Q", self.html)
            self.assertIn(
                self.fx.CommitteeQuestionData.arts_committee_question_one.question[0:30],
                self.html,
            )
            self.assertIn("All questions to the President", self.html)
            self.assertIn(
                "All questions to the %s" % MinisterData.minister_of_arts.name,
                self.html,
            )
        finally:
            db.session.delete(question)
            committee.additional_ministers = []
            db.session.commit()

    def containsCommitteeMeetings(self):
        self.assertIn("Committee meetings", self.html)
        self.assertIn(self.fx.CommitteeMeetingData.arts_meeting_one.title, self.html)
        self.assertIn(self.fx.CommitteeMeetingData.arts_meeting_two.title, self.html)

    def containsCallsForComments(self):
        self.assertIn("Calls for comment", self.html)
        self.assertIn(
            self.fx.CallForCommentData.arts_call_for_comment_one.title, self.html
        )

    def containsTabledReports(self):
        self.assertIn("Tabled reports", self.html)
        self.assertIn(
            self.fx.TabledCommitteeReportData.arts_tabled_committee_report_one.title,
            self.html,
        )

    def containsQuestionsAndReplies(self):
        self.assertIn("Questions and replies", self.html)
        self.assertIn(
            self.fx.CommitteeQuestionData.arts_committee_question_one.code, self.html
        )
        self.assertIn(
            self.fx.CommitteeQuestionData.arts_committee_question_one.asked_by_name,
            self.html,
        )
        self.assertIn(
            self.fx.CommitteeQuestionData.arts_committee_question_one.question[0:30],
            self.html,
        )

    def containsBills(self):
        self.assertIn("Bills", self.html)
        self.assertIn(self.fx.BillData.sport.title, self.html)

    def containsAttendance(self):
        self.assertIn("Attendance", self.html)
        