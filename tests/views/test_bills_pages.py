from urllib.parse import urlparse
import datetime

from tests import PMGLiveServerTestCase
from pmg.models import db, BillStatus
from tests.fixtures import dbfixture, BillData, BillStatusData


class TestBillsPages(PMGLiveServerTestCase):
    def setUp(self):
        super(TestBillsPages, self).setUp()

        self.fx = dbfixture.data(BillStatusData, BillData)
        self.fx.setup()
        self.current_statuses = [status.name for status in BillStatus.current()]
        self.status_dict = {
            "na": ("in progress", "label-primary"),
            "ncop": ("in progress", "label-primary"),
            "assent": ("submitted to the president", "label-warning"),
            "enacted": ("signed into law", "label-success"),
            "withdrawn": ("withdrawn", "label-default"),
            "lapsed": ("lapsed", "label-default"),
        }

    def tearDown(self):
        self.fx.teardown()
        super(TestBillsPages, self).tearDown()

    def test_bills_page(self):
        """
        Test bills page (/bills)
        """
        self.make_request("/bills", follow_redirects=True)
        headings = [
            "Current Bills",
            "All Tabled Bills",
            "Private Member &amp; Committee Bills",
            "All Tabled &amp; Draft Bills",
            "Draft Bills",
            "Bills Explained",
        ]
        for heading in headings:
            self.assertIn(heading, self.html)

    def test_current_bills_page(self):
        """
        Test current bills page (/bills/current)
        """
        self.make_request("/bills/current", follow_redirects=True)
        self.assertIn("Current Bills", self.html)
        self.assertIn("Weekly update for all current bills", self.html)
        for bill_key in self.fx.BillData:
            bill = getattr(self.fx.BillData, bill_key[0])
            if bill.status and bill.status.name in self.current_statuses:
                self.contains_bill(bill)
            else:
                self.doesnt_contain_bill(bill)

    def test_draft_bills_page(self):
        """
        Test draft bills page (/bills/draft/) redirects to current year's 
        draft bills page.
        """
        response = self.make_request("/bills/draft/", follow_redirects=False)
        self.assertEqual(302, response.status_code)
        current_year = datetime.datetime.today().year
        self.assertEqual(
            urlparse(response.location).path, "/bills/draft/year/%d/" % current_year
        )

    def test_draft_bills_page_for_year(self):
        """
        Test draft bills page for a year (/bills/draft/<year>).
        """
        year = 2019
        response = self.make_request(
            "/bills/draft/year/%d/" % year, follow_redirects=True
        )
        self.assertEqual(200, response.status_code)
        bill = self.fx.BillData.draft
        self.assertIn(bill.title, self.html)

    def test_bills_explained_page(self):
        response = self.make_request("/bills/explained/", follow_redirects=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("The Legislative Process", self.html)

    def contains_bill(self, bill):
        self.assertIn(bill.title, self.html)
        if bill.type and "Private Member Bill" in bill.type.name:
            self.assertIn(bill.type.name, self.html, "Page should display bill type")
        elif bill.introduced_by and "Committee" in bill.introduced_by:
            self.assertIn(
                "Committee Bill",
                self.html,
                "Page should display 'Committee Bill' for bills introduced by a committee.",
            )

        if bill.status:
            if bill.status.name in self.status_dict:
                self.assertIn(
                    self.status_dict[bill.status.name][0],
                    self.html,
                    "Page should display correct bill status.",
                )
            else:
                self.assertIn(
                    bill.status.name,
                    self.html,
                    "Page should display correct bill status.",
                )

    def doesnt_contain_bill(self, bill):
        self.assertNotIn(bill.title, self.html)
