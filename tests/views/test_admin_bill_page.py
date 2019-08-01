from tests import PMGLiveServerTestCase
from pmg.models import db
from tests.fixtures import (
    dbfixture, UserData, RoleData, BillData
)


class TestAdminBillPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestAdminBillPage, self).setUp()

        self.fx = dbfixture.data(
            RoleData, UserData, BillData
        )
        self.fx.setup()
        self.user = self.fx.UserData.admin

    def tearDown(self):
        self.fx.teardown()
        super(TestAdminBillPage, self).tearDown()

    def test_admin_bill_page(self):
        """
        Test admin bill page (http://pmg.test:5000/admin/bill)
        """
        self.get_page_contents_as_user(self.user, "http://pmg.test:5000/admin/bill")
        self.assertIn('Bills', self.html)
        self.containsBill(self.fx.BillData.farm)
        self.containsBill(self.fx.BillData.food)
    
    def containsBill(self, bill):
        self.assertIn(bill.title, self.html)
        self.assertIn(bill.type.name, self.html)
        self.assertIn(bill.code, self.html)