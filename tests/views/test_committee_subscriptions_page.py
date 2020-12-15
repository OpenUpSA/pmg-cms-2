import datetime
from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData

THIS_YEAR = datetime.datetime.today().year


class TestCommitteeSubscriptionsPage(PMGLiveServerTestCase):
    def test_committee_subscriptions_page(self):
        """
        Test committee subscriptions page (/committee-subscriptions)
        """
        self.make_request("/committee-subscriptions", follow_redirects=True)
        self.assertIn(
            "Access to meeting reports for premium committees from before {} is freely accessible to everyone.".format(
                THIS_YEAR - 1
            ),
            self.html,
        )
