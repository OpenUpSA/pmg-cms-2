from itertools import groupby

from flask import url_for


ICONS = {
    "member": "bill-introduced.png",
    "committee": "committee-discussion.png",
    "house": "house.png",
    "president": "signed-by-president.png",
    "unknown": "bill-introduced.png",
    }

def get_location(event):
    if event['type'] == 'bill-signed':
        return {'name': 'Office of the President'}

    if 'house' in event:
        return {'name': event['house']['name']}

    if 'committee' in event:
        return {
            'name': event['committee']['name'],
            'url': url_for('committee_detail', committee_id=event['committee']['id']),
        }

    return {'name': 'Unknown'}

def get_agent(event):
    info = None

    if event['type'] == 'bill-signed':
        info = {
            'name': 'The President',
            'type': 'president',
        }

    elif 'member' in event:
        info = {
            'name': event['member']['name'],
            'type': 'member',
            'url': url_for('member', member_id=event['member']['id'])
        }

    elif 'committee' in event:
        info = {
            'name': event['committee']['name'],
            'type': 'committee',
            'url': url_for('committee_detail', committee_id=event['committee']['id'])
        }

    elif 'house' in event:
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
    events.sort(key=lambda e: [e['date'], get_location(e), get_agent(e)])

    for location, location_events in groupby(events, get_location):
        location_history = []

        for agent, agent_events in groupby(location_events, get_agent):
            info = {'events': list(agent_events)}
            info.update(agent)
            location_history.append(info)

        info = {'events': location_history}
        info.update(location)
        history.append(info)

    return history
