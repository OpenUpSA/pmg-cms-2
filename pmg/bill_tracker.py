import json
import datetime
from pmg.models.resources import Bill


# Simple export of bill data to pmg/static/bill-tracker.json
def produce_bill_tracker_json():
    bills = []
    for bill in Bill.query.order_by(Bill.year).limit(1000000000).all():
        billDict = {
            "id": bill.id,
            "title": bill.title,
            "type": bill.type.name,
            "status": "draft",
            "year": bill.year,
            "introduced_by": bill.introduced_by,
            "date_of_introduction": bill.date_of_introduction,
            "events": [],
            "versions": [],
        }

        if bill.status:
            billDict["status"] = bill.status.name

        # Order bill.events by event.date
        events = sorted(bill.events, key=lambda x: x.date)
        for event in events:
            bill_event = {
                "id": event.id,
                "title": event.title,
                "date": event.date,
                "type": event.type,
                "public_participation": event.public_participation,
            }
            if event.member:
                bill_event["member"] = event.member.name

            if event.type in ["bill-signed", "bill-act-commenced", "bill-enacted"]:
                bill_event["house"] = "President"
            elif event.house:
                bill_event["house"] = event.house.name_short
            elif event.committee:
                bill_event["house"] = event.committee.house.name_short

            if event.committee:
                bill_event["committee"] = event.committee.name

            billDict["events"].append(bill_event)

        for version in bill.versions:
            bill_version = {
                "id": version.id,
                "date": version.date,
                "title": version.title,
                "enacted": version.enacted,
            }
            billDict["versions"].append(bill_version)
        bills.append(billDict)
    with open("pmg/static/bill-tracker.json", "w") as f:
        json.dump(bills, f, indent=4, ensure_ascii=False, default=str)
