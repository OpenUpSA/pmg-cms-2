import os
import json
import time, datetime
import parsers
import logging
import csv
import re
import requests
from sqlalchemy import types
from backend.app import app, db
from backend.models import *
from backend.search import Search
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import Date, cast


def strip_rtf(rtf_str):
        if rtf_str:
            return unicode(rtf_str.replace('\\"', '').replace('\\r', '').replace('\\n', '').replace('\\t', ''))
        else:
            return None


def capture_meeting_report_nids():

    i = 0
    duplicate_count = 0
    not_found_count = 0
    db.session.commit()
    logger.debug("reading report.json")
    with open('data/report.json', 'r') as f:
        for line in f.readlines():
            i += 1
            report = json.loads(line)
            nid = int(report.get('nid'))
            title = strip_rtf(report.get('title'))

            date = None
            try:
                timestamp = int(report['meeting_date'].strip('"'))
                date = datetime.datetime.fromtimestamp(timestamp, tz=tz.gettz('UTC'))
            except (TypeError, AttributeError, KeyError) as e:
                pass

            if nid and title:
                try:
                    tmp_query = CommitteeMeeting.query.filter_by(title=title)
                    if date:
                        tmp_query = tmp_query.filter_by(date=date)
                    committee_meeting = tmp_query.one()
                    committee_meeting.nid = nid
                    db.session.add(committee_meeting)
                except NoResultFound as e:
                    not_found_count += 1
                except MultipleResultsFound as e:
                    duplicate_count += 1
                    pass
            if i % 100 == 0:
                print "saving 100 committee meeting reports to the db (" + str(i) + " so far)"
                db.session.commit()
            if i % 1000 == 0:
                print duplicate_count, "duplicates could not be matched"
                print not_found_count, "reports could not be found at all"
    db.session.commit()
    print duplicate_count, "duplicates could not be matched"
    print not_found_count, "reports could not be found at all"
    return


def db_date_from_utime(utime):
    try:
        return datetime.datetime.fromtimestamp(float(utime))
    except:
        try:
            datetime.strptime(utime, '%Y-%m-%dT%H:%m:%s')
        except:
            return None


def capture_hansard_nids():

    duplicates = []
    not_found = []
    with open('data/hansard.json', 'r') as f:
        i = 0
        lines = f.readlines()
        logger.debug("Found %i records" % (len(lines)))
        for line in lines:
            i += 1
            try:
                hansard = json.loads(line)
                nid = hansard['nid']
                try:
                    hansard_obj = Hansard.query.filter_by(title=title).one()
                    if hansard_obj:
                        hansard_obj.nid = nid
                        db.session.add(hansard_obj)
                except MultipleResultsFound as e:
                    duplicates.append((nid, title))
                    pass
                except NoResultFound as e:
                    not_found.append((nid, title))
                    pass
                if i % 100 == 0:
                    db.session.commit()
                    logger.debug("Wrote 100 rows...")
            except Exception as e:
                print e
                logger.warning("Error reading row")
    db.session.commit()
    print "\nduplicates: " + str(len(duplicates))
    print json.dumps(duplicates, indent=4)
    print "\nnot found: " + str(len(not_found))
    print json.dumps(not_found, indent=4)


def capture_briefing_nids():

    duplicates = []
    not_found = []
    with open('data/briefing.json', 'r') as f:
        i = 0
        lines = f.readlines()
        logger.debug("Found %i records" % (len(lines)))
        for line in lines:
            i += 1
            try:
                briefing = json.loads(line)
                title = briefing["title"]
                nid = briefing['nid']
                try:
                    briefing_obj = Briefing.query.filter_by(title=title).one()
                    if briefing_obj:
                        briefing_obj.nid = nid
                        db.session.add(briefing_obj)
                except MultipleResultsFound as e:
                    duplicates.append((nid, title))
                    pass
                except NoResultFound as e:
                    not_found.append((nid, title))
                    pass
                if i % 100 == 0:
                    db.session.commit()
                    logger.debug("Wrote 100 rows...")
            except Exception as e:
                print e
                logger.warning("Error reading row")
    db.session.commit()
    print "\nduplicates: " + str(len(duplicates))
    print json.dumps(duplicates, indent=4)
    print "\nnot found: " + str(len(not_found))
    print json.dumps(not_found, indent=4)


if __name__ == '__main__':

    Search.reindex_changes = False
    capture_hansard_nids()
    capture_briefing_nids()

