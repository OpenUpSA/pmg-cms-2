from datetime import date
import dateutil.parser
import logging

import arrow
from flask import request, url_for

from frontend import app
from frontend.ga import get_ga_events

logger = logging.getLogger(__name__)

@app.context_processor
def pagination_processor():
    def pagination(page_count, current_page, per_page, url):
        # Source:
        # https://github.com/jmcclell/django-bootstrap-pagination/blob/master/bootstrap_pagination/templatetags/bootstrap_pagination.py#L154
        range_length = 15
        logger.debug("Building pagination")
        if range_length is None:
            range_min = 1
            range_max = page_count
        else:
            if range_length < 1:
                raise Exception(
                    "Optional argument \"range\" expecting integer greater than 0")
            elif range_length > page_count:
                range_length = page_count
            range_length -= 1
            range_min = max(current_page - (range_length / 2) + 1, 1)
            range_max = min(current_page + (range_length / 2) + 1, page_count)
            range_diff = range_max - range_min
            if range_diff < range_length:
                shift = range_length - range_diff
                if range_min - shift > 0:
                    range_min -= shift
                else:
                    range_max += shift
        page_range = range(range_min, range_max + 1)
        s = ""
        for i in page_range:
            active = ""
            if ((i - 1) == current_page):
                active = "active"
            query_string = ""
            if (request.query_string):
                query_string = "?" + request.query_string
            s += "<li class='{0}'><a href='{1}/{2}/{4}'>{3}</a></li>".format(
                active,
                url,
                i -
                1,
                i,
                query_string)
        return s
    return dict(pagination=pagination)


@app.template_filter('pretty_date')
def _jinja2_filter_datetime(iso_str, format_option=None):
    if not iso_str:
        return ""
    format = '%d %b %Y'
    if format_option == "long":
        format = '%d %B %Y'
    date = dateutil.parser.parse(iso_str)
    return date.strftime(format)


@app.template_filter('member_url')
def _jinja2_filter_member_url(member):
    if member.get('pa_url'):
        return member['pa_url']
    return url_for('member', member_id=member['id'])


@app.template_filter('search_snippet')
def _jinja2_filter_search_snippet(snippet):
    if not snippet:
        return ""
    if isinstance(snippet, list):
        snippet = ' ... '.join(snippet)
    return snippet


@app.template_filter('ellipse')
def _jinja2_filter_ellipse(snippet):
    return "...&nbsp;" + snippet.strip() + "&nbsp;..."


@app.template_filter('nbsp')
def _jinja2_nbsp(str):
    return str.replace(" ", "&nbsp;")


@app.template_filter('human_date')
def _jinja2_filter_humandate(iso_str):
    if not iso_str:
        return ""
    return arrow.get(iso_str).humanize()

@app.context_processor
def get_ga_events_helper():
    return {'get_ga_events': get_ga_events}
