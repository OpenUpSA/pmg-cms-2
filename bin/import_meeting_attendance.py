#!/bin/env python

import argparse
import os
import sys
import csv
import time
import datetime
import arrow
from collections import defaultdict
from sqlalchemy import func

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg import db
from pmg.models.resources import CommitteeMeeting, Member, Committee, House, CommitteeMeetingAttendance

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Import Committee meeting attendance csv file')
    parser.add_argument('input', help='Path of file to import')
    parser.add_argument('log', help='Path of file to log errors')
    args = parser.parse_args()

    meeting_count = defaultdict(list)
    with open(args.input) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # To be used for checking multiple committee meetings in a single day
            if row['ISSID'] not in meeting_count[(row['Date'], row['Name Committee'])]:
                meeting_count[(row['Date'], row['Name Committee'])].append(row['ISSID'])


    with open(args.log, 'wb') as logfile:
        with open(args.input) as csvfile:
            # The csv file being imported should be sorted by date.
            writer = csv.writer(logfile)
            reader = csv.DictReader(csvfile)

            members = Member.query.all()
            all_committees = Committee.query.all()
            ncop_committees = Committee.query.filter(House.name_short == 'NCOP')

            member_dict = {}
            committee_dict = {}
            committee_meeting_dict = {}

            for row in reader:
                if reader.line_num >= 10:
                    if len(meeting_count[(row['Date'], row['Name Committee'])]) > 1:
                        writer.writerow([
                            row['Column'], row['AET'], row['AST'], row['Date'],
                            row['House'], row['ISSID'], row['Name Committee'],
                            row['OST'], row['PMG Name'], row['alt'], row['attendance'],
                            row['chairperson'], row['first_name'], row['party_affiliation'],
                            row['province'], row['surname'], row['title']])
                        continue

                    ost = row['OST'] if row['OST'] else '00:00:00'
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
                    committee_name = row['Name Committee']

                    if member_name in member_dict:
                        member = member_dict[member_name]
                    else:
                        # Check for some member exceptions
                        if "%s, %s %s" % (last_name, title, first_name[0]) == "Mandela, Mr Z":
                            member = Member.query.filter(Member.name == "Mandela, Nkosi ZM").first()
                        elif "%s, %s %s" % (last_name, title, first_name[0]) == "Kohler, Ms D":
                            member = Member.query.filter(Member.name == "Kohler-Barnard, Ms D").first()
                        elif "%s, %s %s" % (last_name, title, first_name[0]) == "Mthethwa, Mr E":
                            member = Member.query.filter(Member.name == "Mthethwa, Mr EM").first()
                        # Temp: These members are currently not on the system
                        elif "%s, %s %s" % (last_name, title, first_name[0]) == "Michael, Ms N":
                            member = None
                        elif "%s, %s %s" % (last_name, title, first_name[0]) == "Bernard, Mr J":
                            member = None
                        elif "%s, %s %s" % (last_name, title, first_name[0]) == "Oriani-Ambrosini, Mr M":
                            member = None
                        else:
                            member = Member.find_by_inexact_name(first_name, last_name, title, members=members)
                        member_dict[member_name] = member

                    if 'Portfolio Committee on' in committee_name or 'Porrfolio Committee on' in committee_name:
                            # Remove from committee_name as it doesn't appear in the db
                            prefix_len = len('Portfolio Committee on')
                            committee_name = committee_name[prefix_len+1:]

                    if committee_name in committee_dict:
                        committee = committee_dict[committee_name]
                    else:
                        # Check for some committee exceptions
                        if committee_name == 'Standing Committee on Finance':
                            committee = Committee.query.filter(Committee.name == "Finance Standing Committee").first()
                        elif committee_name == 'Select Committee on Finance':
                            committee = Committee.query.filter(Committee.name == 'NCOP Finance').first()
                        elif committee_name == 'Select Committee on Economic Development':
                            committee = Committee.query.filter(Committee.name == 'NCOP Economic and Business Development').first()
                        elif committee_name == 'Select Committee on Appropriations':
                            committee = Committee.query.filter(Committee.name == 'NCOP Appropriations').first()
                        elif committee_name == 'Select Committee on Social Services':
                            committee = Committee.query.filter(Committee.name == 'NCOP Social Services').first()
                        elif committee_name == 'Ad hoc Committee on Powers and Privileges  of Parlaiment':
                            committee = Committee.query.filter(Committee.name == 'Powers and Privileges').first()
                        elif committee_name == 'Public Services and Administration':
                            committee = Committee.query.filter(Committee.name == 'Public Service and Administration, as well as Performance Monitoring and Evaluation').first()
                        elif committee_name == 'Joint Standing Committee on Defence':
                            committee = Committee.query.filter(Committee.name == 'Defence').first()
                        elif committee_name == 'Ad Hoc Committee on Open Democracy Bill':
                            committee = Committee.query.filter(
                                Committee.name == 'Promotion of Access to Information Bill (Open Democracy Bill)').first()
                        # Temp: these committees do not exist
                        elif committee_name == 'Ad Hoc Committee Nkandla':
                            committee = None
                            # committee = Committee.query.filter(
                            #     Committee.name == 'Ad Hoc Committee on Police Minister\'s Report on Nkandla').first()
                        elif committee_name == 'Standing committee of Public accounts':
                            committee = None
                        elif 'Select Committee on' in committee_name:
                            # Only campare against NCOP committees
                            committee = Committee.find_by_inexact_name(committee_name, candidates=ncop_committees)
                        else:
                            committee = Committee.find_by_inexact_name(committee_name, candidates=all_committees)
                        committee_dict[committee_name] = committee

                    if committee:
                        if (committee.name, meeting_date.date()) in committee_meeting_dict:
                            committee_meeting_results = committee_meeting_dict[(committee.name, meeting_date.date())]
                        else:
                            committee_meeting_results = CommitteeMeeting.query\
                                .filter(CommitteeMeeting.committee == committee)\
                                .filter(func.date(CommitteeMeeting.date) == meeting_date.date())\
                                .all()
                            if committee_meeting_results:
                                cm = committee_meeting_results[0]
                                committee_meeting_dict[(cm.committee.name, cm.date.date())] = committee_meeting_results
                    else:
                        committee_meeting_results = []

                    if len(committee_meeting_results) != 1:
                        # If multiple, or no meetings were found, log the row.
                        writer.writerow([
                            row['Column'], row['AET'], row['AST'], row['Date'],
                            row['House'], row['ISSID'], row['Name Committee'],
                            row['OST'], row['PMG Name'], row['alt'], row['attendance'],
                            row['chairperson'], row['first_name'], row['party_affiliation'],
                            row['province'], row['surname'], row['title']
                        ])
                        print "Meetings error: " + str(reader.line_num)
                        print "Number of Comittee meetings: " + str(len(committee_meeting_results))

                    elif member is None:
                        writer.writerow([
                            row['Column'], row['AET'], row['AST'], row['Date'],
                            row['House'], row['ISSID'], row['Name Committee'],
                            row['OST'], row['PMG Name'], row['alt'], row['attendance'],
                            row['chairperson'], row['first_name'], row['party_affiliation'],
                            row['province'], row['surname'], row['title']
                        ])
                        print "Member error: " + str(reader.line_num)

                    else:
                        committee_meeting = committee_meeting_results[0]
                        committee_meeting.date = meeting_date
                        committee_meeting.actual_start_time = ast
                        committee_meeting.actual_end_time = aet

                        committee_meeting_attendance = CommitteeMeetingAttendance(
                            alternate_member=alternate_member,
                            attendance=attendance,
                            chairperson=chairperson,
                            meeting=committee_meeting,
                            member=member
                        )
                        db.session.add(committee_meeting_attendance)
                        print reader.line_num

                    if reader.line_num % 10 == 0:
                        db.session.flush()

            db.session.flush()
            #db.session.commit()
