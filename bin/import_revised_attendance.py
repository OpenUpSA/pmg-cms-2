#!/bin/env python

import argparse
import os
import sys
import csv
import time
import datetime
import arrow
import re

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg import db
from pmg.models.resources import CommitteeMeeting, Member, CommitteeMeetingAttendance


def log_error(writer, row, error=None):
    row['new_error'] = error
    writer.writerow([
        row['Column'], row['AET'], row['AST'], row['Date'],
        row['House'], row['ISSID'], row['Name Committee'],
        row['OST'], row['PMG Name'], row['alt'], row['attendance'],
        row['chairperson'], row['first_name'], row['party_affiliation'],
        row['province'], row['surname'], row['title'], row['error'],
        row['url'], row['url2'], row['comments'], row['new_error']
    ])

def get_member(members, first_name, last_name, title):
    # Check for some member exceptions
    if "%s, %s %s" % (last_name, title, first_name[0]) == "Mandela, Mr Z":
        member = Member.query.filter(Member.name == "Mandela, Nkosi ZM").first()
    elif "%s, %s %s" % (last_name, title, first_name[0]) == "Kohler, Ms D":
        member = Member.query.filter(Member.name == "Kohler-Barnard, Ms D").first()
    elif "%s, %s %s" % (last_name, title, first_name[0]) == "Mthethwa, Mr E":
        member = Member.query.filter(Member.name == "Mthethwa, Mr EM").first()
    else:
        member = Member.find_by_inexact_name(first_name, last_name, title, members=members)
    return member


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Committee meeting attendance csv file')
    parser.add_argument('input', help='Path of file to import')
    parser.add_argument('log', help='Path of file to log errors')
    args = parser.parse_args()

    with open(args.log, 'wb') as logfile:
        with open(args.input) as csvfile:

            writer = csv.writer(logfile)
            reader = csv.DictReader(csvfile)

            members = Member.query.all()
            member_dict = {}
            committee_meeting_dict = {}
            meeting_attendance = list()

            for row in reader:
                if reader.line_num >= 0:
                    # Temp: Member mismatches
                    if row['surname'] in ["Ramakatsa", "Michael"]:
                        log_error(writer, row, error='Member incorrectly matched.')
                        continue

                    if row['url'] == "Committee meeting not found.":
                        log_error(writer, row)
                        continue

                    if row['error'] == 'Member not found.':
                        first_name = row['first_name']
                        last_name = row['surname']
                        title = row['title']
                        member_name = "%s, %s %s" % (last_name, title, first_name[0])

                        if member_name in member_dict:
                            member = member_dict[member_name]
                        else:
                            member = get_member(members, first_name, last_name, title)
                            member_dict[member_name] = member
                        if not member:
                            # Member not found
                            log_error(writer, row)
                            continue
                        pass

                    elif row['url2']:
                        log_error(writer, row)
                        continue

                    elif not row['url']:
                        log_error(writer, row)
                        continue

                    ost = row['OST'] if row['OST'] else '00:00:00'
                    if not re.match(r'^\d\d:', ost):
                        ost = '0' + ost

                    # force GMT+0200
                    date_time_str = "%sT%s+02:00" % (row['Date'], ost)
                    meeting_date = arrow.get(date_time_str).datetime
                    try:
                        aet = time.strptime(row['AET'], '%H:%M:%S')
                        aet = datetime.time(aet.tm_hour, aet.tm_min, tzinfo=meeting_date.tzinfo)
                    except ValueError:
                        aet = None
                    try:
                        ast = time.strptime(row['AST'], '%H:%M:%S')
                        ast = datetime.time(ast.tm_hour, ast.tm_min, tzinfo=meeting_date.tzinfo)
                    except ValueError:
                        ast = None

                    if row['alt'] == 'Y':
                        alternate_member = True
                    elif row['alt'] == 'N':
                        alternate_member = False
                    else:
                        alternate_member = None

                    attendance = row['attendance'] or 'U'

                    if row['chairperson'] == 'TRUE':
                        chairperson = True
                    if row['chairperson'] == 'FALSE':
                        chairperson = False

                    first_name = row['first_name']
                    last_name = row['surname']
                    title = row['title']
                    member_name = "%s, %s %s" % (last_name, title, first_name[0])

                    if member_name in member_dict:
                        member = member_dict[member_name]
                    else:
                        member = get_member(members, first_name, last_name, title)
                        member_dict[member_name] = member

                    if not member:
                        # Member not found
                        log_error(writer, row, error='Member not found.')
                        continue

                    committee_meeting_id = int(row['url'].strip("https://pmg.org.za/committee-meeting/"))
                    committee_meeting = CommitteeMeeting.query.get(committee_meeting_id)

                    committee_meeting.date = meeting_date
                    committee_meeting.actual_start_time = ast
                    committee_meeting.actual_end_time = aet

                    if not (committee_meeting.id, member.id) in meeting_attendance:
                        meeting_attendance.append((committee_meeting.id, member.id))

                        existing_attendance = CommitteeMeetingAttendance.query\
                            .filter(CommitteeMeetingAttendance.meeting_id == committee_meeting.id)\
                            .filter(CommitteeMeetingAttendance.member_id == member.id).first()

                        if not existing_attendance:
                            committee_meeting_attendance = CommitteeMeetingAttendance(
                                alternate_member=alternate_member,
                                attendance=attendance,
                                chairperson=chairperson,
                                meeting=committee_meeting,
                                member=member)

                            db.session.add(committee_meeting_attendance)
                            print 'Adding attendance: %s' % (reader.line_num)
                        else:
                            print 'Attendance exists: %s' % (reader.line_num)
                    else:
                        log_error(writer, row, error='Duplicate member for meeting in sheet.')
                        continue

                    # if reader.line_num % 10 == 0:
                    #     db.session.flush()

            # db.session.flush()
            db.session.commit()

