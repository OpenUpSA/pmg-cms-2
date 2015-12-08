#!/bin/env python
# -*- coding: utf-8 -*-

""" Script to ensure that events mentioning bills in their
titles are correctly linked to those bills.
"""
import re


from pmg.models import Event, Bill, db
from pmg.search import Search
from sqlalchemy.orm import subqueryload

Search.reindex_changes = False


BILL_RE = re.compile(u'bill[, ]*\[(B|PMB)\s*(\d+)(\s*[a-z])?[\s–-]+(\d\d\d\d)', re.IGNORECASE)


def fixbills():
    fixed = 0
    bills = Bill.query.all()
    # index by year and num
    bills = {b.code: b for b in bills if b.number}

    events = Event.query\
        .filter(Event.title.ilike('%bill%'))\
        .options(subqueryload('bills'))\
        .all()

    for event in events:
        for match in BILL_RE.finditer(event.title):
            prefix = match.group(1)
            num = int(match.group(2))
            year = int(match.group(4))
            code = '%s%s-%s' % (prefix, num, year)

            bill = bills.get(code)
            if bill:
                if bill not in event.bills:
                    event.bills.append(bill)
                    fixed += 1
                    print "Matched %s [%s] (%d) to %s (%d)" % (bill.code, bill.title, bill.id, event.title, event.id)
            else:
                print "No bill %s" % code

    print "Fixed %d links" % fixed
    db.session.commit()


if __name__ == '__main__':
    fixbills()
