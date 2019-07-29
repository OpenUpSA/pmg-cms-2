from tests import PMGLiveServerTestCase
from tests.fixtures import (
    dbfixture, HouseData, CommitteeData
)


class TestCommitteesPage(PMGLiveServerTestCase):
    def setUp(self):
        super(TestCommitteesPage, self).setUp()

        self.fx = dbfixture.data(
            HouseData, CommitteeData, 
        )
        self.fx.setup()

    def tearDown(self):
        self.fx.teardown()
        super(TestCommitteesPage, self).tearDown()

    def test_committees_page(self):
        self.get_page_contents("http://pmg.test:5000/committees")
        self.assertIn('Parliamentary Committees', self.html)
        self.assertIn(self.fx.CommitteeData.communications.name, self.html)
        self.assertIn(self.fx.CommitteeData.arts.name, self.html)
        self.assertIn(self.fx.CommitteeData.constitutional_review.name, self.html)
        headings = ['National Assembly', 'Joint',
                    'National Council of Provinces', 'Ad-hoc']
        for heading in headings:
            self.assertIn(heading, self.html)