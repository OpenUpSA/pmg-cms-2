from tests import PMGTestCase
from pmg.models import db, Bill, BillType, BillStatus, Event, House, Member, Committee
from pmg.bills import bill_history
from datetime import datetime, timedelta


class TestHansardLink(PMGTestCase):
    def setUp(self):
        super(TestHansardLink, self).setUp()
        bill_type = BillType(name="Section 74", prefix="B", description="Section 74")
        bill_status = BillStatus(
            name="president",
            description="Approved by Parliament. Waiting to be signed into law.",
        )
        house_na = House(name="National Assembly", name_short="NA", sphere="national")
        house_ncop = House(
            name="National Counsil Of Provinces", name_short="NCOP", sphere="national"
        )

        db.session.add(bill_type)
        db.session.add(bill_status)
        db.session.add(house_na)
        db.session.add(house_ncop)
        db.session.commit()

        bill = Bill(
            title="Food and Health Bill",
            number=1,
            year=2019,
            introduced_by="National Assembly",
            place_of_introduction=house_na,
            date_of_introduction=datetime.today().date() - timedelta(days=5),
            status=bill_status,
            type=bill_type,
        )

        db.session.add(bill)
        db.session.commit()

        event_na_passed = Event(
            date=datetime.now() - timedelta(days=1),
            title="Bill passed by National Assembly",
            type="bill-passed",
            house=house_na,
            bills=[bill],
        )
        event_na_introduced = Event(
            date=datetime.now() - timedelta(days=5),
            title="Bill introduced to the National Assembly",
            type="bill-introduced",
            house=house_na,
            bills=[bill],
        )
        event_ncop_passed = Event(
            date=datetime.now() - timedelta(days=2),
            title="Bill passed by both Houses",
            type="bill-passed",
            house=house_ncop,
            bills=[bill],
        )
        event_hansard_passed_na = Event(
            date=datetime.now() - timedelta(days=1),
            title="NA: Unrevised",
            type="plenary",
            house=house_na,
            bills=[bill],
        )
        event_hansard_passed_ncop = Event(
            date=datetime.now() - timedelta(days=2),
            title="NCOP: Unrevised",
            type="plenary",
            house=house_ncop,
            bills=[bill],
        )
        db.session.add(event_na_passed)
        db.session.add(event_na_introduced)
        db.session.add(event_ncop_passed)
        db.session.add(event_hansard_passed_na)
        db.session.add(event_hansard_passed_ncop)

        db.session.commit()

    def test_hansard_link(self):
        bill = Bill.query.filter_by(title="Food and Health Bill").first()
        request = self.client.get(
            "v2/bills/%s" % bill.id, base_url="http://api.pmg.test:5000/"
        )
        bill_history_result = bill_history(request.json["result"])
        # Amount of class house generated: 2 NA, 1 NCOP
        self.assertEqual(3, len(bill_history_result))

        # Checking that the NCOP has got 1 event and that it has linked a hansard
        for event_class in bill_history_result:
            if event_class["class"] == "NCOP":
                self.assertEqual(1, len(event_class["events"]))
                self.assertTrue("hansard" in event_class["events"][0]["events"][0])

                # check that the correct hansard has been linked.
                event = Event.query.filter_by(title="NCOP: Unrevised").first()
                self.assertEqual(
                    event.id, event_class["events"][0]["events"][0]["hansard"]["id"]
                )
