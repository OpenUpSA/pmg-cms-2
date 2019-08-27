from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, HouseData, CommitteeData
)


class TestEmailAlertsPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestEmailAlertsPage, self).setUp()

        self.fx = dbfixture.data(
            HouseData, CommitteeData,
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestEmailAlertsPage, self).tearDown()

    def test_email_alerts_page(self):
        """
        Test email alerts page (/email-alerts)
        """
        self.get_page_contents("http://pmg.test:5000/email-alerts")
        self.assertIn('Which committees should we send you email alerts for?',
                      self.html)
        self.assertIn('National Assembly', self.html)
        self.assertIn(self.fx.CommitteeData.communications.name, self.html)
        self.assertIn('National Council of Provinces', self.html)
        self.assertIn('Provincial Legislatures Committees', self.html)
        self.assertIn(
            self.fx.CommitteeData.western_cape_budget.name, self.html)
        self.assertIn('Ad-Hoc Committees', self.html)
