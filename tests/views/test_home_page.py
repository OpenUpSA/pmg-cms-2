from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, MemberData, FeaturedData, PageData, CommitteeMeetingData,
    BillData
)
from flask import url_for


class TestHomePage(PMGLiveServerTestCase):
    NAVIGATION = [
        'Committees and Meetings',
        'MPs',
        'Bills',
        'Questions and Replies',
        'Calls for Comments',
        'Attendance',
        'Blog',
        'Provincial Legislatures',
    ]

    def setUp(self):
        super(TestHomePage, self).setUp()

        self.fx = dbfixture.data(
            MemberData, FeaturedData, PageData, CommitteeMeetingData, BillData
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestHomePage, self).tearDown()

    def test_members_page(self):
        """
        Test home page (http://pmg.test:5000/home)
        """
        self.get_page_contents(
            "http://pmg.test:5000"
        )
        for navigation in self.NAVIGATION:
            self.assertIn(navigation, self.html, 'Page should contain navigation heading "%s"' % navigation)
        
        self.containsFeaturedContent()
        self.containsSearchBanner()
        self.containsRecentCommitteeMeetings()
        self.containsCurrentBills()
        self.containsRecentQuestionsAndReplies()
        self.containsRecentBlogs()
    
    def containsHomeBanner(self):
        self.assertIn(self.fx.FeaturedData.the_week_ahead.title, self.html)
        self.assertIn(self.fx.FeaturedData.current_bills.title, self.html)

    def containsFeaturedContent(self):
        self.assertIn('Featured Content', self.html, 'Page should contain featured content section.')

        self.assertIn(self.fx.PageData.section_25_review_process.title, self.html)
        self.assertNotIn(self.fx.PageData.un_featured_page.title, self.html)

        self.containsFeaturedCommitteeMeeting()

    def containsFeaturedCommitteeMeeting(self):
        meeting = self.fx.CommitteeMeetingData.arts_meeting_two
        url = url_for('committee_meeting', event_id=meeting.id, via='homepage-feature-card')
        self.assertIn(meeting.title[0:100], self.html)
        self.assertIn(meeting.committee.name, self.html)
        self.assertIn(meeting.committee.house.name, self.html)
        self.assertIn(url, self.html)

    def containsSearchBanner(self):
        self.assertIn('Search the PMG website', self.html)

    def containsRecentCommitteeMeetings(self):
        self.assertIn('Recent Committee Meetings', self.html)
        self.containsRecentCommitteeMeeting(self.fx.CommitteeMeetingData.arts_meeting_one)
        self.containsRecentCommitteeMeeting(self.fx.CommitteeMeetingData.arts_meeting_two)

    def containsRecentCommitteeMeeting(self, meeting):
        url = url_for('committee_meeting', event_id=meeting.id, via='homepage-card')
        self.assertIn(url, self.html)
        self.assertIn(meeting.committee.name, self.html)
        self.assertIn(meeting.committee.house.name, self.html)
        self.assertIn(meeting.title[0:100], self.html)

    def containsCurrentBills(self):
        self.assertIn('Current Bills', self.html)
        self.assertIn('More bills', self.html)
        self.containsCurrentBill(self.fx.BillData.food)
        self.doesNotContainUnCurrentBill(self.fx.BillData.farm)
    
    def containsCurrentBill(self, bill):
        self.assertIn(bill.title, self.html)
        self.assertIn(bill.introduced_by, self.html)

    def doesNotContainUnCurrentBill(self, bill):
        self.assertNotIn(bill.title, self.html)

    def containsRecentQuestionsAndReplies(self):
        self.assertIn('Recent Questions and Replies', self.html)

    def containsRecentBlogs(self):
        self.assertIn('Recent Blogs', self.html)