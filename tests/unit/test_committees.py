from tests import PMGTestCase
from pmg.models import Committee


class TestCommittees(PMGTestCase):
    def test_get_display_name_for_active_committee(self):
        active_committee = Committee(name="Arts and Culture", active=True)
        self.assertEqual("Arts and Culture", active_committee.get_display_name())

    def test_get_display_name_for_inactive_committee(self):
        inactive_committee = Committee(name="Communications", active=False)
        self.assertEqual("Communications (Inactive)", inactive_committee.get_display_name())
