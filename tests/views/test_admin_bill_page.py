from builtins import str
from tests import PMGLiveServerTestCase
import unittest
from pmg.models import db, BillType, Minister, Bill
from tests.fixtures import (
    dbfixture,
    UserData,
    RoleData,
    BillData,
    HouseData,
    BillTypeData,
)
import html


class TestAdminBillPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminBillPage, self).setUp()

        self.fx = dbfixture.data(RoleData, UserData, BillData, HouseData, BillTypeData)
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.delete_created_objects()
        self.fx.teardown()
        super(TestAdminBillPage, self).tearDown()

    def test_admin_bill_page(self):
        """
        Test admin bill page (/admin/bill)
        """
        self.make_request("/admin/bill", self.user, follow_redirects=True)
        self.assertIn("Bills", self.html)
        self.containsBill(self.fx.BillData.farm)
        self.containsBill(self.fx.BillData.food)

    def containsBill(self, bill):
        self.assertIn(bill.title, self.html)
        self.assertIn(bill.type.name, self.html)
        self.assertIn(bill.code, self.html)

    def test_admin_create_bill(self):
        """
        Create a bill with the admin interface (/admin/bill/new/)
        """
        before_count = len(Bill.query.all())
        url = "/admin/bill/new/?url=%2Fadmin%2Fbill%2F"
        data = {
            "year": "2020",
            "title": "Cool Bill",
            "type": str(self.fx.BillTypeData.section_74.id),
            "introduced_by": "James",
            "date_of_introduction": "2019-07-03",
            "place_of_introduction": str(self.fx.HouseData.na.id),
            "date_of_assent": "2019-07-03",
            "effective_date": "2019-07-03",
            "act_name": "Fundamental",
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Bill.query.all())
        self.assertEqual(302, response.status_code)
        self.assertLess(before_count, after_count)

        created_bill = Bill.query.filter(Bill.title == data["title"]).scalar()
        self.assertTrue(created_bill)
        self.created_objects.append(created_bill)

    def test_admin_create_bill_event_titles_help_section(self):
        """
        The admin bill create page should show help text for
        which bill event title are allowed when the bill type is "bill-passed".
        """
        url = "/admin/bill/new"
        response = self.make_request(url, self.user, follow_redirects=True)

        self.assertIn(html.escape("Help?"), self.html)
        self.assertIn(
            "When event type is &#34;Bill passed&#34;, event title must be one of",
            self.html,
        )
        self.assertIn(
            "Bill passed by the National Assembly and transmitted to the "
            "NCOP for concurrence",
            self.html,
        )

    def test_admin_action_bill(self):
        """
        Delete a bill with the admin interface (/admin/bill/action/)
        """
        before_count = len(Bill.query.all())
        url = "/admin/bill/action/"
        data = {
            "url": "/admin/bill/",
            "action": "delete",
            "rowid": [
                str(self.fx.BillData.food.id),
            ],
        }
        response = self.make_request(url, self.user, data=data, method="POST")
        after_count = len(Bill.query.all())
        self.assertEqual(302, response.status_code)
        self.assertGreater(before_count, after_count)

    def test_admin_delete_bill(self):
        """
        Delete a bill on the admin interface
        (/admin/bill/delete/)
        """
        before_count = len(Bill.query.all())
        url = "/admin/bill/delete/"
        data = {
            "url": "/admin/bill/",
            "id": str(self.fx.BillData.food.id),
        }
        response = self.make_request(
            url, self.user, follow_redirects=True, data=data, method="POST"
        )
        after_count = len(Bill.query.all())
        self.assertEqual(200, response.status_code)
        self.assertGreater(before_count, after_count)

    def test_admin_edit_bill(self):
        """
        Edit a bill with the admin interface (/admin/bill/edit/)
        """
        bill = db.session.query(Bill).first()
        new_title = "Cool Bill"
        url = "/admin/bill/edit/?id=%d" % bill.id
        data = {
            "year": "2020",
            "title": new_title,
            "type": str(self.fx.BillTypeData.section_74.id),
            "introduced_by": "James",
            "date_of_introduction": "2019-07-03",
            "place_of_introduction": str(self.fx.HouseData.na.id),
            "date_of_assent": "2019-07-03",
            "effective_date": "2019-07-03",
            "act_name": "Fundamental",
        }
        response = self.make_request(
            url, self.user, follow_redirects=True, data=data, method="POST"
        )
        self.assertEqual(200, response.status_code)

        db.session.refresh(bill)
        self.assertEqual(new_title, bill.title)
