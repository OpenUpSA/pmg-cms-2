from tests import PMGLiveServerTestCase
from pmg.models import BillStatus
from tests.fixtures import (
    dbfixture,
    MemberData,
    FeaturedData,
    PageData,
    CommitteeMeetingData,
    BillData,
    CommitteeQuestionData,
    PostData,
)
from flask import url_for


class TestHomePage(PMGLiveServerTestCase):
    NAVIGATION = [
        "Committees and Meetings",
        "MPs",
        "Bills",
        "Questions and Replies",
        "Calls for Comments",
        "Attendance",
        "Blog",
        "Provincial Legislatures",
    ]

    def setUp(self):
        super(TestHomePage, self).setUp()

        self.fx = dbfixture.data(
            MemberData,
            FeaturedData,
            PageData,
            CommitteeMeetingData,
            BillData,
            CommitteeQuestionData,
            PostData,
        )
        self.fx.setup()
        self.current_statuses = [status.name for status in BillStatus.current()]

    def tearDown(self):
        self.fx.teardown()
        super(TestHomePage, self).tearDown()

    def test_members_page(self):
        """
        Test home page (/home)
        """
        self.make_request("/")
        for navigation in self.NAVIGATION:
            self.assertIn(
                navigation,
                self.html,
                'Page should contain navigation heading "%s"' % navigation,
            )

        self.contains_featured_content()
        self.contains_search_banner()
        self.contains_recent_committee_meetings()
        self.contains_bills()
        self.contains_recent_questions_and_replies()
        self.contains_recent_blogs()

    def contains_home_banner(self):
        self.assertIn(self.fx.FeaturedData.the_week_ahead.title, self.html)
        self.assertIn(self.fx.FeaturedData.current_bills.title, self.html)

    def contains_featured_content(self):
        self.assertIn(
            "Featured Content",
            self.html,
            "Page should contain featured content section.",
        )

        self.assertIn(self.fx.PageData.section_25_review_process.title, self.html)
        self.assertNotIn(self.fx.PageData.un_featured_page.title, self.html)

        self.contains_featured_committee_meeting()

    def contains_featured_committee_meeting(self):
        meeting = self.fx.CommitteeMeetingData.arts_meeting_two
        url = url_for(
            "committee_meeting", event_id=meeting.id, via="homepage-feature-card"
        )
        self.assertIn(meeting.title[0:100], self.html)
        self.assertIn(meeting.committee.name, self.html)
        self.assertIn(meeting.committee.house.name, self.html)
        self.assertIn(url, self.html)

    def contains_search_banner(self):
        self.assertIn("Search the PMG website", self.html)

    def contains_recent_committee_meetings(self):
        self.assertIn("Recent Committee Meetings", self.html)
        self.contains_recent_committee_meeting(
            self.fx.CommitteeMeetingData.arts_meeting_one
        )
        self.contains_recent_committee_meeting(
            self.fx.CommitteeMeetingData.arts_meeting_two
        )

    def contains_recent_committee_meeting(self, meeting):
        url = url_for("committee_meeting", event_id=meeting.id, via="homepage-card")
        self.assertIn(url, self.html)
        self.assertIn(meeting.committee.name, self.html)
        self.assertIn(meeting.committee.house.name, self.html)
        self.assertIn(meeting.title[0:100], self.html)

    def contains_bills(self):
        self.assertIn("Current Bills", self.html)
        self.assertIn("More bills", self.html)
        for bill_key in self.fx.BillData:
            bill = getattr(self.fx.BillData, bill_key[0])
            if bill.status and bill.status.name in self.current_statuses:
                self.contains_bill(bill)
            else:
                self.doesnt_contain_bill(bill)

    def contains_bill(self, bill):
        self.assertIn(bill.title, self.html)
        if bill.introduced_by:
            self.assertIn(bill.introduced_by, self.html)

    def doesnt_contain_bill(self, bill):
        self.assertNotIn(
            bill.title,
            self.html,
            'Home page should not contain bills that doesn\'t have a "current" status.',
        )

    def contains_recent_questions_and_replies(self):
        self.assertIn("Recent Questions and Replies", self.html)
        self.contains_question(
            self.fx.CommitteeQuestionData.arts_committee_question_one
        )

    def contains_question(self, question):
        self.assertIn(question.question_to_name, self.html)
        self.assertIn(question.question[:80], self.html)

    def contains_recent_blogs(self):
        self.assertIn("Recent Blogs", self.html)
        self.contains_post(self.fx.PostData.the_week_ahead)

    def contains_post(self, post):
        self.assertIn(post.title, self.html)
        self.assertIn(post.body[:80], self.html)
