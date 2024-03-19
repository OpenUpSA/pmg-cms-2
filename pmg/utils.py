import re

import nltk
from universal_analytics import Tracker, HTTPRequest
from flask import request
from flask_security import current_user
import requests
import json
import os

# Useragents that are bots
BOTS_RE = re.compile("(bot|spider|cloudfront|slurp)", re.I)


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
    """User Google Analytics to track this pageview."""
    from pmg import app

    ga_id = app.config.get("GOOGLE_ANALYTICS_ID")
    if not ga_id:
        return False

    user_agent = request.user_agent.string
    if ignore_bots and BOTS_RE.search(user_agent):
        return False

    path = path or request.path
    user_id = current_user.id if current_user.is_authenticated else None

    client_id = request.cookies.get("_ga")
    if client_id:
        # GA1.2.1760224793.1424413995
        client_id = client_id.split(".", 2)[-1]

    with HTTPRequest() as http:
        tracker = Tracker(ga_id, http, user_id=user_id, client_id=client_id)
        response = tracker.send(
            "pageview",
            path,
            uip=request.access_route[0],
            referrer=request.referrer or "",
            userAgent=user_agent,
        )

    return True


def track_file_download():
    from pmg import app

    ga_url = "https://www.google-analytics.com/mp/collect"
    ga_id = app.config.get("GOOGLE_ANALYTICS_ID")
    api_secret = app.config.get("GOOGLE_ANALYTICS_API_SECRET")
    client_id = request.cookies.get("_ga")

    path = request.path
    last_slash_index = path.rfind("/")
    file_dir = path[:last_slash_index]
    page_location = f"{request.url_root}{file_dir[1:]}"

    url = f"{ga_url}?measurement_id={ga_id}&api_secret={api_secret}"
    payload = {
        "client_id": client_id,
        "non_personalized_ads": "false",
        "events": [
            {
                "name": "file_download",
                "params": {
                    "file_extension": path.split(".")[-1],
                    "file_name": path,
                    "link_url": request.url,
                    "page_location": page_location,
                    "page_referrer": request.referrer,
                },
            }
        ],
    }
    requests.post(url, data=json.dumps(payload), verify=True)

    return True


def externalise_url(url):
    """Externalise a URL based on the request scheme and host."""
    from pmg import app

    if url.startswith("http"):
        url = url.split("/", 3)[3]

    if url.startswith("/"):
        url = url[1:]

    scheme = "http" if app.config["DEBUG"] else "https"
    return "%s://%s/%s" % (scheme, request.host, url)


def slugify_province(prov):
    """
    Province name to slug i.e. lowercase, and spaces to dashes.
    """
    return prov.replace(" ", "-").lower()


def deslugify_province(prov):
    """
    Province slug to name, i.e. dashes to spaces and title case.
    KZN is a special case.
    """
    if prov == "kwazulu-natal":
        return "KwaZulu-Natal"
    return prov.replace("-", " ").title()
