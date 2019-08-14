from tests import PMGTestCase
from pmg.models import db, Committee
from tests.fixtures import (
    dbfixture, CommitteeData
)


class TestCommittees(PMGTestCase):
    def setUp(self):
        super(TestCommittees, self).setUp()
        self.fx = dbfixture.data(
            CommitteeData,
        )
        self.fx.setup()
    
    def tearDown(self):
        self.fx.teardown()
        super(TestCommittees, self).tearDown()

    def test_get_display_name(self):
        for committee in self.fx.CommitteeData:
            self.check_committee(committee[1])

    def check_committee(self, committee):
        if not committee.active:
            self.assertEqual(committee.name + " (Inactive)", committee.get_display_name())
        else:
            self.assertIn(committee.name, committee.get_display_name())
