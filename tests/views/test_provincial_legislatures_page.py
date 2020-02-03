from tests import PMGLiveServerTestCase
from tests.fixtures import dbfixture, HouseData, CommitteeData, DailyScheduleData
from pmg.models import House
from pmg.views import utils


class TestProvincialLegislaturesPages(PMGLiveServerTestCase):
    def setUp(self):
        super(TestProvincialLegislaturesPages, self).setUp()

        self.fx = dbfixture.data(HouseData, CommitteeData, DailyScheduleData)
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

    def test_provincial_programme(self):
        """
        Test provincial programme page (/provincial-legislatures/<slug>/programme/<int:programme_id>/)
        """
        slug = utils.slugify_province(self.fx.HouseData.western_cape.name)
        programme = self.fx.DailyScheduleData.schedule_one
        self.make_request(
            "/provincial-legislatures/%s/programme/%s" % (slug, programme.id),
            follow_redirects=True,
        )
        self.assertIn(programme.title, self.html)

    def test_provincial_programmes(self):
        """
        Test provincial programmes page (/provincial-legislatures/<slug>/programmes/)
        """
        slug = utils.slugify_province(self.fx.HouseData.western_cape.name)
        programme = self.fx.DailyScheduleData.schedule_one
        self.make_request(
            "/provincial-legislatures/%s/programmes/" % (slug),
            follow_redirects=True,
        )
        self.assertIn("Programmes", self.html)
        self.assertIn(programme.title, self.html)
