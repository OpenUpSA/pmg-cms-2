from __future__ import division
import re

import nltk
from UniversalAnalytics import Tracker
from flask import request
from flask.ext.security import current_user


# Useragents that are bots
BOTS_RE = re.compile('(bot|spider|cloudfront|slurp)', re.I)


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


def track_pageview(path=None, ignore_bots=True):
    """ User Google Analytics to track this pageview. """
    from pmg import app

    ga_id = app.config.get('GOOGLE_ANALYTICS_ID')
    if not ga_id:
        return False

    user_agent = request.user_agent.string
    if ignore_bots and BOTS_RE.search(user_agent):
        return False

    path = path or request.path
    user_id = current_user.id if current_user.is_authenticated() else None

    client_id = request.cookies.get('_ga')
    if client_id:
        # GA1.2.1760224793.1424413995
        client_id = client_id.split('.', 2)[-1]

    tracker = Tracker.create(ga_id, user_id=user_id, client_id=client_id)
    tracker.send('pageview', path,
                 uip=request.access_route[0],
                 referrer=request.referrer or '',
                 userAgent=user_agent)

    return True


def externalise_url(url):
    """ Externalise a URL based on the request scheme and host.
    """
    if url.startswith('http'):
        url = url.split('/', 3)[3]
    return '%s://%s/%s' % (request.scheme, request.host, url)
