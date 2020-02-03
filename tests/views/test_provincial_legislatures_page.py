from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData
from pmg.models import House
from pmg.views import utils


class TestProvincialLegislaturesPages(PMGLiveServerTestCase):
    def setUp(self):
        super(TestProvincialLegislaturesPages, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData)
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestProvincialLegislaturesPages, self).tearDown()

    def test_provincial_legislatures_page(self):
        """
        Test provincial legislatures page (/provincial-legislatures/)
        """
        self.make_request(
            "/provincial-legislatures/",
            follow_redirects=True,
        )
        self.assertIn("Provincial Legislatures", self.html)
        self.assertIn(self.fx.HouseData.western_cape.name, self.html)

    def test_provincial_legislature_page_for_province(self):
        """
        Test provincial legislatures page (/provincial-legislatures/<province>)
        """
        slug =  utils.slugify_province(self.fx.HouseData.western_cape.name)
        self.make_request(
            "/provincial-legislatures/%s" % slug,
            follow_redirects=True,
        )
        self.assertIn("Provincial Legislatures", self.html)
        self.assertIn(self.fx.HouseData.western_cape.name, self.html)
        self.assertIn("Committees", self.html)
        self.assertIn("Members", self.html)