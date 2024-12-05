from itertools import groupby
import datetime
import os.path
import bisect
import iso8601

from flask import url_for

MIN_YEAR = 2006


ICONS = {
    "member": "bill-introduced.png",
    "committee": "committee-discussion.png",
    "house": "house.png",
    "president": "signed-by-president.png",
    "unknown": "bill-introduced.png",
    "concourt": "bill-concourt.png",
}


def get_location(event):
    if event.get("type") in ["bill-signed", "bill-act-commenced", "bill-enacted"]:
        return {
            "name": "Office of the President",
            "class": "president",
        }

    if event.get("type") == "bill-concourt":
        return {
            "name": "Constitutional Court",
            "class": "concourt",
        }

    if event.get("house"):
        return {
            "name": event["house"]["name"],
            "class": event["house"]["short_name"],
        }

    if event.get("committee"):
        if "house" in event["committee"]:
            return {
                "name": event["committee"]["house"]["name"],
                "class": event["committee"]["house"]["short_name"],
            }

        return {
            "name": event["committee"]["name"],
            "url": url_for("committee_detail", committee_id=event["committee"]["id"]),
            "class": "",
        }

    return {"name": "Unknown", "class": ""}


def get_agent(event, bill):
    info = {}

    if event.get("type") in ["bill-signed", "bill-act-commenced", "bill-enacted"]:
        info = {
            "name": "The President",
            "type": "president",
        }

    elif event.get("type") == "bill-introduced":
        info = {
            "name": bill["introduced_by"]
            or (bill.get("place_of_introduction") or {}).get("name"),
            "type": "member",
        }

    elif event.get("member"):
        info = {
            "name": event["member"]["name"],
            "type": "member",
            "url": url_for("member", member_id=event["member"]["id"]),
        }

    elif event.get("committee"):
        info = {
            "name": event["committee"]["name"],
            "type": "committee",
            "url": url_for("committee_detail", committee_id=event["committee"]["id"]),
        }

    elif event.get("house"):

        if event["house"]["short_name"] == "concourt":
            info = {
                "name": "Constitutional Court",
                "type": "concourt",
            }
        else:
            info = {
                "name": event["house"]["name"],
                "type": "house",
            }
    else:
        info = {"name": "Unknown", "type": "unknown"}

    info["icon"] = ICONS[info["type"]]

    return info


def bill_history(bill):
    """ Work out the history of a bill and return a description of it. """
    history = []

    events = bill.get("events", [])
    events.sort(
        key=lambda e: [
            iso8601.parse_date(e["date"]),
            get_location(e).get("name", ""),
            get_agent(e, bill).get("name", ""),
        ]
    )

    for location, location_events in groupby(events, get_location):
        location_history = []

        for agent, agent_events in groupby(
            location_events, lambda e: get_agent(e, bill)
        ):
            info = {"events": list(agent_events)}
            info.update(agent)
            location_history.append(info)

        info = {"events": location_history}
        info.update(location)
        history.append(info)

    history = hansard_linking(history)
    return history


def match_title(event_title):
    """
    Match bill title against the following possible titles
    """
    bill_titles = [
        "bill amended and passed by ncop",
        "bill passed and amended by ncop",
        "bill passed and amended by the ncop",
        "bill passed and referred to the ncop",
        "bill passed and sent to the president for assent",
        "bill passed and submitted to the ncop",
        "bill passed by both",
        "bill passed by na",
        "bill passed by national assembly",
        "bill passed by national council of provinces",
        "bill passed by ncop",
        "bill passed by parliament",
        "bill passed by the national assembly",
        "bill passed by the national council of provinces",
        "bill passed by the ncop",
        "bill passed with proposed amendments",
        "bill revived on this date",
        "the ncop rescinded",
        "bill remitted",
        "bill revived on this date",
        "the na rescinded",
        "bill rejected",
        "the na granted permission",
        "the ncop granted permission",
        "bill lapsed",
        "bill withdrawn"
    ]
    event_title_lower = event_title.strip().lower()
    for title in bill_titles:
        if event_title_lower.startswith(title):
            return True
    return False


def match_dates(hansard_date, event_date):
    hansard_iso_date = iso8601.parse_date(hansard_date)
    event_iso_date = iso8601.parse_date(event_date)
    return hansard_iso_date.date() == event_iso_date.date()


def hansard_linking(bill_history):
    """
    We need to link certain bill events to hansards
    Hansards will always be linked to a house (NA or NCOP)
    The Date of the bill event and the hansard will be the same.

    If the event(bill_passed etc) is matched, a new dict is created with the 
    matching hansard id.
    The Hansard event is not modified.
    """

    for class_history in bill_history:
        for event_history in class_history["events"]:
            if event_history["type"] == "house":
                bill_events = [
                    e
                    for e in event_history["events"]
                    if e["type"] != "plenary" and match_title(e["title"])
                ]
                hansard_events = [
                    e for e in event_history["events"] if e["type"] == "plenary"
                ]
                for bill_event in bill_events:
                    for hansard_event in hansard_events:
                        if match_dates(hansard_event["date"], bill_event["date"]):
                            bill_event["hansard"] = {"id": hansard_event["id"]}
                            break
    return bill_history


def count_parliamentary_days(date_from, date_to):
    """ Count the number of parliamentary days between two dates, inclusive.
    """
    i = bisect.bisect(PARLIAMENTARY_DAYS, date_from)
    j = bisect.bisect(PARLIAMENTARY_DAYS, date_to)
    return j - i + 1


def load_parliamentary_days():
    """ Load the dates when parliament sat from data/parliament-sitting-days.txt

    This file can be updated from a spreadsheet using bin/load_parliamentary_days.py
    """
    with open(
        os.path.join(os.path.dirname(__file__), "../data/parliament-sitting-days.txt"),
        "r",
    ) as f:
        lines = f.readlines()
        dates = [datetime.date(*(int(x) for x in d.split("-"))) for d in lines]
        return sorted(dates)


PARLIAMENTARY_DAYS = load_parliamentary_days()
