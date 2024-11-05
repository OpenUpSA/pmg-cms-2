from builtins import str
from builtins import range
from datetime import date, datetime
import dateutil.parser
import logging

import arrow
from flask import request, url_for

from pmg import app
from pmg.ga import get_ga_events
from pmg.forms import CorrectThisPageForm
import pytz


logger = logging.getLogger(__name__)

SAST = pytz.timezone("Africa/Johannesburg")


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
                    'Optional argument "range" expecting integer greater than 0'
                )
            elif range_length > page_count:
                range_length = page_count
            range_length -= 1
            range_min = max(current_page - (range_length // 2) + 1, 1)
            range_max = min(current_page + (range_length // 2) + 1, page_count)
            range_diff = range_max - range_min
            if range_diff < range_length:
                shift = range_length - range_diff
                if range_min - shift > 0:
                    range_min -= shift
                else:
                    range_max += shift
        page_range = list(range(range_min, range_max + 1))
        s = ""
        for i in page_range:
            active = ""
            if (i - 1) == current_page:
                active = "active"
            query_string = ""
            if request.query_string:
                query_string = "?" + request.query_string.decode("utf-8")
            s += "<li class='{0}'><a href='{1}/{2}/{4}'>{3}</a></li>".format(
                active, url, i - 1, i, query_string
            )
        return s

    return dict(pagination=pagination)


@app.template_filter("pretty_date")
def _jinja2_filter_datetime(iso_str, format_option=None):
    if not iso_str:
        return ""

    if not isinstance(iso_str, (date, datetime)):
        d = dateutil.parser.parse(iso_str)
    else:
        d = iso_str

    if isinstance(d, datetime):
        d = d.astimezone(SAST)

    format = "%d %b %Y"
    if format_option == "long":
        format = "%d %B %Y"
    elif format_option == "ga":
        # format for google analytics dimension2
        # we exclude the day because it makes it easier
        # to use in GA, and the day isn't all that useful
        # as an reporting axis
        format = "%Y-%m"

    return d.strftime(format)


@app.template_filter("member_url")
def _jinja2_filter_member_url(member):
    if member.get("pa_url"):
        return member["pa_url"]
    return url_for("member", member_id=member["id"])


@app.template_filter("search_snippet")
def _jinja2_filter_search_snippet(snippet, mark=None):
    if not snippet:
        return ""
    if isinstance(snippet, list):
        snippet = " ... ".join(snippet)
    if mark is not None:
        snippet = snippet.replace("mark>", "%s>" % mark)
    return snippet


@app.template_filter("ellipse")
def _jinja2_filter_ellipse(snippet):
    return "...&nbsp;" + snippet.strip() + "&nbsp;..."


@app.template_filter("nbsp")
def _jinja2_nbsp(str):
    return str.replace(" ", "&nbsp;")


@app.template_filter("human_date")
def _jinja2_filter_humandate(iso_str):
    if not iso_str:
        return ""
    return arrow.get(iso_str).humanize()


@app.context_processor
def get_ga_events_helper():
    return {"get_ga_events": get_ga_events}


@app.context_processor
def feedback_form():
    if request:
        form = CorrectThisPageForm()
    else:
        form = None
    return {"correct_this_page_form": form}


@app.context_processor
def inject_paths():
    context_vars = {
        "STATIC_HOST": app.config["STATIC_HOST"],
    }
    return context_vars


@app.template_filter("add_commas")
def jinja2_filter_add_commas(quantity):
    out = ""
    quantity_str = str(quantity)
    while len(quantity_str) > 3:
        tmp = quantity_str[-3::]
        out = "," + tmp + out
        quantity_str = quantity_str[0:-3]
    return quantity_str + out


@app.template_filter("dir")
def jinja2_filter_dir(value):
    res = []
    for k in dir(value):
        res.append("%r %r\n" % (k, getattr(value, k)))
    return "<br>".join(res)


@app.template_filter("is_file")
def jinja2_filter_is_file(content_obj):
    logger.debug("IS_FILE")
    logger.debug(content_obj)
    if content_obj.file:
        return True
    return False
