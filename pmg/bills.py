from itertools import groupby
import datetime
import os.path
import bisect

from flask import url_for

MIN_YEAR = 2006


ICONS = {
    "member": "bill-introduced.png",
    "committee": "committee-discussion.png",
    "house": "house.png",
    "president": "signed-by-president.png",
    "unknown": "bill-introduced.png",
}


def get_location(event):
    if event.get('type') in ['bill-signed', 'bill-act-commenced', 'bill-enacted']:
        return {
            'name': 'Office of the President',
            'class': 'president',
        }

    if event.get('house'):
        return {
            'name': event['house']['name'],
            'class': event['house']['short_name'],
        }

    if event.get('committee'):
        if 'house' in event['committee']:
            return {
                'name': event['committee']['house']['name'],
                'class': event['committee']['house']['short_name'],
            }

        return {
            'name': event['committee']['name'],
            'url': url_for('committee_detail', committee_id=event['committee']['id']),
            'class': '',
        }

    return {'name': 'Unknown', 'class': ''}


def get_agent(event, bill):
    info = None

    if event.get('type') in ['bill-signed', 'bill-act-commenced', 'bill-enacted']:
        info = {
            'name': 'The President',
            'type': 'president',
        }

    elif event.get('type') == 'bill-introduced':
        info = {
            'name': bill['introduced_by'] or (bill.get('place_of_introduction') or {}).get('name'),
            'type': 'member',
        }

    elif event.get('member'):
        info = {
            'name': event['member']['name'],
            'type': 'member',
            'url': url_for('member', member_id=event['member']['id'])
        }

    elif event.get('committee'):
        info = {
            'name': event['committee']['name'],
            'type': 'committee',
            'url': url_for('committee_detail', committee_id=event['committee']['id'])
        }

    elif event.get('house'):
        info = {
            'name': event['house']['name'],
            'type': 'house',
        }
    else:
        info = {'name': 'Unknown', 'type': 'unknown'}

    info['icon'] = ICONS[info['type']]

    return info


def bill_history(bill):
    """ Work out the history of a bill and return a description of it. """
    history = []

    events = bill.get('events', [])
    events.sort(key=lambda e: [e['date'], get_location(e), get_agent(e, bill)])

    for location, location_events in groupby(events, get_location):
        location_history = []

        for agent, agent_events in groupby(location_events, lambda e: get_agent(e, bill)):
            info = {'events': list(agent_events)}
            info.update(agent)
            location_history.append(info)

        info = {'events': location_history}
        info.update(location)
        history.append(info)

    return history


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
    with open(os.path.join(os.path.dirname(__file__), "../data/parliament-sitting-days.txt"), "r") as f:
        lines = f.readlines()
        dates = [datetime.date(*(int(x) for x in d.split("-"))) for d in lines]
        return sorted(dates)


PARLIAMENTARY_DAYS = load_parliamentary_days()
