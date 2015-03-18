from flask import session

def ga_event(category, action, label=None, value=None):
    """Stores an Google Analytics event in the session that can be
    fetched (and cleared) using :func:`get_ga_events`.
    """
    events = session.get('_gaevents', [])
    events.append((category, action, label, value))
    session['_gaevents'] = events

def get_ga_events():
    """ Get (and clear) Google Analytics events stored with :func:`ga_event`.
    """
    return session.pop('_gaevents', [])
