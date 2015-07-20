#!/bin/env python

import argparse
import os
import sys
import csv
import time
import datetime
import pytz
from dateutil.tz import tzutc
from sqlalchemy import func

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg import db
from pmg.models.resources import CommitteeMeeting, Member, Committee, House, CommitteeMeetingAttendance

if __name__ == "__main__":

    # parser = argparse.ArgumentParser(description='Import Committee meeting attendance csv file')
    # parser.add_argument('csv_file', help='Path to file')
    # args = parser.parse_args()
    # if args.csv_file:

    with open(file_path + '/output.csv', 'wb') as outputfile:
        with open(file_path + '/test.csv') as csvfile:
            # The csv file being imported needs to be sorted by date.
            writer = csv.writer(outputfile)
            reader = csv.DictReader(csvfile)

            members = Member.query.all()
            all_committees = Committee.query.all()
            ncop_committees = Committee.query.filter(House.name_short == 'NCOP')

            local_time = pytz.timezone('Africa/Johannesburg')

            member_dict = {}
            committee_dict = {}
            # import ipdb; ipdb.set_trace()
            for row in reader:
                import ipdb; ipdb.set_trace()
                if reader.line_num < 2000:
                    date_time_str = "%s %s" % (row['Date'], row['OST'])
                    try:
                        meeting_date = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
                        meeting_date = meeting_date.replace(tzinfo=local_time)
                    except ValueError:
                        # No OST
                        meeting_date = datetime.datetime.strptime(row['Date'], '%Y-%m-%d')
                        meeting_date = meeting_date.replace(tzinfo=local_time)
                    try:
                        aet = time.strptime(row['AET'], '%H:%M:%S')
                        aet = datetime.time(aet.tm_hour, aet.tm_min, tzinfo=local_time)
                    except ValueError:
                        aet = None
                    try:
                        ast = time.strptime(row['AST'], '%H:%M:%S')
                        ast = datetime.time(ast.tm_hour, ast.tm_min, tzinfo=local_time)
                    except ValueError:
                        ast = None

                    if row['alt'] == 'Y':
                        alternate_member = True
                    elif row['alt'] == 'N':
                        alternate_member = False
                    else:
                        alternate_member = None

                    attendance = row['attendance']

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

                    if committee_name in committee_dict:
                        commitee = committee_dict[committee_name]
                    else:
                        # Check for some committee exceptions
                        if 'Portfolio Committee on' in committee_name or 'Porrfolio Committee on' in committee_name:
                            prefix_len = len('Portfolio Committee on')
                            committee_name = committee_name[prefix_len+1:]
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

                        # Temp: these committees do not exist
                        elif committee_name == 'Ad Hoc Committee Nkandla':
                            committee = None
                            # committee = Committee.query.filter(
                            #     Committee.name == 'Ad Hoc Committee on Police Minister\'s Report on Nkandla').first()
                        elif committee_name == 'Standing committee of Public accounts':
                            committee = None
                        elif committee_name == 'Ad Hoc Committee on Open Democracy Bill':
                            committee = Committee.query.filter(
                                Committee.name == 'Promotion of Access to Information Bill (Open Democracy Bill)').first()
                        elif 'Select Committee on' in committee_name:
                            committee = Committee.find_by_inexact_name(committee_name, candidates=ncop_committees)
                        else:
                            committee = Committee.find_by_inexact_name(committee_name, candidates=all_committees)
                        committee_dict[committee_name] = committee

                    committee_meeting_results = CommitteeMeeting.query\
                                .filter(CommitteeMeeting.committee == committee)\
                                .filter(func.date(CommitteeMeeting.date) == meeting_date.date())\
                                .all()

                    if len(committee_meeting_results) != 1:
                        # If multiple, or no meetings were found, log the row.
                        writer.writerow([
                            row['Column'], row['AET'], row['AST'], row['Date'],
                            row['House'], row['ISSID'], row['Name'], row['Committee'],
                            row['OST'], row['PMG'], row['Name'], row['alt'], row['attendance'],
                            row['chairperson'], row['first_name'], row['party_affiliation'],
                            row['province'], row['surname'], row['title']
                        ])
                        print "Errornous line: " + str(reader.line_num)
                        print "Number of Comittee meetings: " + str(len(committee_meeting_results))
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

            db.session.flush()
            # db.session.commit()
