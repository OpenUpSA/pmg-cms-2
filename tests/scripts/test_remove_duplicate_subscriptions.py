from tests import PMGTestCase
from tests.fixtures import dbfixture, CommitteeData, OrganisationData
from pmg.models.users import organisation_committee
from pmg.models import db
from bin.remove_duplicate_subscriptions import remove_duplicate_subscriptions


class TestRemoveDuplicateSubscriptions(PMGTestCase):
    def setUp(self):
        super().setUp()
        # Create the fixtures
        self.fx = dbfixture.data(CommitteeData, OrganisationData)
        self.fx.setup()

    def test_run_remove_duplicate_subscriptions(self):
        organisation = self.fx.OrganisationData.pmg

        # Create a duplicate subscription
        insert = organisation_committee.insert().values(
            committee_id=self.fx.CommitteeData.arts.id, organisation_id=organisation.id,
        )
        db.session.execute(insert)
        insert = organisation_committee.insert().values(
            committee_id=self.fx.CommitteeData.arts.id, organisation_id=organisation.id,
        )
        db.session.execute(insert)

        # Create a non-duplicate subscription
        insert = organisation_committee.insert().values(
            committee_id=self.fx.CommitteeData.constitutional_review.id,
            organisation_id=organisation.id,
        )
        db.session.execute(insert)

        # Run the command
        remove_duplicate_subscriptions()

        # Check that only one of each subscription now exists (i.e. duplicates
        # have been removed).
        c = (
            db.session.query(organisation_committee)
            .filter(
                organisation_committee.c.committee_id == self.fx.CommitteeData.arts.id
            )
            .filter(organisation_committee.c.organisation_id == organisation.id)
            .count()
        )
        self.assertEquals(1, c)
        c = (
            db.session.query(organisation_committee)
            .filter(
                organisation_committee.c.committee_id
                == self.fx.CommitteeData.constitutional_review.id
            )
            .filter(organisation_committee.c.organisation_id == organisation.id)
            .count()
        )
        self.assertEquals(1, c)
