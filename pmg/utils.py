from __future__ import division

import nltk
from UniversalAnalytics import Tracker
from flask import request
from flask.ext.security import current_user


def levenshtein(first, second, transpositions=False):
    """
    Return a similarity ratio of two pieces of text. 0 means the strings are not similar at all,
    1.0 means they're identical. This is the Levenshtein ratio:
      (lensum - ldist) / lensum
    where lensum is the sum of the length of the two strings and ldist is the
    Levenshtein distance (edit distance).
    See https://groups.google.com/forum/#!topic/nltk-users/u94RFDWbGyw
    """
    lensum = len(first) + len(second)
    ldist = nltk.edit_distance(first, second, transpositions=transpositions)

    if lensum == 0:
        return 0

    return (lensum - ldist) / lensum


def track_pageview(path=None):
    """ User Google Analytics to track this pageview. """
    from pmg import app

    ga_id = app.config.get('GOOGLE_ANALYTICS_ID')
    if not ga_id:
        return

    path = path or request.path
    user_id = current_user.id if current_user.is_authenticated() else None
    client_ip = request.access_route[0]

    client_id = request.cookies.get('_ga')
    if client_id:
        # GA1.2.1760224793.1424413995
        client_id = client_id.split('.', 2)[-1]

    tracker = Tracker.create(ga_id, user_id=user_id, client_id=client_id)
    tracker.send('pageview', path, uip=client_ip)
