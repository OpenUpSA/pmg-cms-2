#!/bin/env python
# -*- coding: utf-8 -*-

""" Script to ensure that hansards mentioning bills in their
titles are correctly linked to those bills.
"""
import re


from pmg.models import Hansard, Bill, db
from pmg.search import Search

Search.reindex_changes = False


BILL_RE = re.compile(u'bill[, ]*\[B\s*(\d+)(\s*[a-z])?[\s–-]+(\d\d\d\d)', re.IGNORECASE)


def fixbills():
    fixed = 0
    bills = Bill.query.all()
    # index by year and num
    bills = {(b.number, b.year): b for b in bills if b.number}

    hansards = Hansard.query.all()

    for hansard in hansards:
        for match in BILL_RE.finditer(hansard.title):
            num = int(match.group(1))
            year = int(match.group(3))

            bill = bills.get((num, year))
            if bill:
                if bill not in hansard.bills:
                    hansard.bills.append(bill)
                    fixed += 1
                    print "Matched %s (%d) to %s (%d)" % (bill.code, bill.id, hansard.title, hansard.id)
            else:
                print "No bill %s - %s" % (num, year)

    print "Fixed %d links" % fixed
    db.session.commit()


if __name__ == '__main__':
    fixbills()
