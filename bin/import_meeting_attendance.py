#!/bin/env python

from __future__ import print_function
from builtins import str
import argparse
import os
import sys
import csv
import time
import datetime
import arrow
import re
from collections import defaultdict
from sqlalchemy import func

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg import db
from pmg.models.resources import CommitteeMeeting, Member, Committee, House, CommitteeMeetingAttendance


"""
To do an import:
----------------

Run check_committees.py and check_members.py
Inspect output to ensure items are being mapped correctly.

Include any incorrect mappings in committee_name_map and member_name_map dicts
Include any missing members or committees in missing_members and missing_committees lists
"""

# Maps for members and committees which get matched incorrectly.

member_name_map = {
    'Mandela, Mr Z': 'Mandela, Nkosi ZM',
    'Mthethwa, Mr E': 'Mthethwa, Mr EM',
    'Michael, Ms N': 'Mazzone, Ms NW',
    'Van Der Merwe, Mr J': 'Van der Merwe, Mr JH',
    'Mpheti, Mr S': 'Mphethi, Mr SSA',
    'Mmola, Ms M': 'MMola, Ms MP',
    'Kohler, Ms D': 'Kohler-Barnard, Ms D',
    'Pilane-majake, Ms M': 'Pilane-Majake, Ms MC',
    'Litchfield-tshabalala, Ms K': 'Litchfield-Tshabalala, Ms K',
    'Madikizela-mandela, Ms N': 'Madikizela-Mandela, Ms NW',
    'Van Der Merwe, Ms L': 'van der Merwe, Ms LL',
    'Ngwenya-mabila, Ms P': 'Ngwenya-Mabila, Ms PC',
    'Moloi-moropa, Ms J': 'Moloi-Moropa, Ms JC',
    'Hill-lewis, Mr G': 'Hill-Lewis, Mr GG',
    'Mpambo-sibhukwana, Ms T': 'Mpambo-Sibhukwana, Ms T',
    'Ramokhoase, Mr T': 'Ramokhoase , Mr TR',
    'Luzipo, Mr S': 'Luzipho, Mr S',
    'Pilane-majake, Ms C': 'Pilane-Majake, Ms MC',
    'Dlamini-dubazana, Ms Z': 'Dlamini-Dubazana, Ms ZS',
    'Mc Gluwa, Mr J': 'McGluwa, Mr JJ',
    'Van Der Westhuizen, Mr A': 'van der Westhuizen, Mr AP',
    'Mente-nqweniso, Ms N': 'Mente-Nqweniso, Ms NV',
    'Scheepers, Ms M': 'Scheepers, Ms MA',
    'Faber, Mr W': 'Faber, Mr WF',
    'Makhubela-mashele, Ms L': 'Makhubela-Mashele, Ms LS',
    'Xego-sovita, Ms S': 'Xego, Ms ST',
    'Mnganga - Gcabashe, Ms L': 'Mnganga-Gcabashe, Ms LA',
    'Bam-mugwanya, Ms V': 'Bam-Mugwanya, Ms V',
    'Steenkamp, Ms J': 'Edwards, Ms J',
    'Tarabella Marchesi, Ms N': 'Tarabella - Marchesi, Ms NI',
    'Shope-sithole, Ms S': 'Shope-Sithole, Ms SC',
    'Mcloughlin, Mr A': 'McLoughlin, Mr AR',
    'Letsatsi-duba, Ms D': 'Letsatsi-Duba, Ms DB',
    'Kekana, Mr HB': 'Kekana, Ms HB',
    'Faber, Mr W': 'Faber, Mr WF',
    'Scheepers, Ms M': 'Scheepers Ms MA'
}

missing_members = [
    'August, Ms C',
    'Bernard, Mr J'
]

committee_name_map = {
    'Portfolio Committee on Police': 'Police',
    'Standing Committee on Finance': 'Finance Standing Committee',
    'Portfolio Committee on Justice and Correctional Services': 'Justice and Correctional Services',
    'Standing Committee on Public Accounts': 'Public Accounts',
    'Portfolio Committee on Sports and Recreation': 'Sport and Recreation',
    'Portfolio Committee on Public Works': 'Public Works',
    'Portfolio Committee on Telecommunicationsand Postal Services': 'Telecommunications and Postal Services',
    'Portfolio Committee on Rural Development and Land Reform': 'Rural Development and Land Reform',
    'Portfolio Committee on the Review of the National Assembly Rules': 'Rules of the National Assembly',
    'Portfolio Committee on Trade and Industry': 'Trade and Industry',
    'Select Committee on Co-operative Governance and Traditional Affairs': 'Cooperative Governance and Traditional Affairs',
    'Portfolio Committee on Communications': 'Communications',
    'Portfolio Committee on Home Affairs': 'Home Affairs',
    'Select Committee on Appropriations': 'NCOP Appropriations',
    'Portfolio Committee on Agriculture, Forestry and Fisheries': 'Agriculture, Forestry and Fisheries',
    'Select Committee on Petitions and Executive Undertakings': 'NCOP Petitions and Executive Undertakings',
    'Portfolio Committee on Small Business and Development': 'Small Business Development',
    'Portfolio Committee on Mineral Resources': 'Mineral Resources',
    'Portfolio Committee on Public Services and Administration': 'Public Service and Administration, as well as Performance Monitoring and Evaluation',
    'Portfolio Committee on Higher Education and Training': 'Higher Education and Training',
    'Portfolio Committee on Health': 'Health',
    'Portfolio Committee on Labour': 'Labour',
    'Portfolio Committee on Social Development': 'Social Development',
    'Select Committee on Trade and International Relations': 'NCOP Trade and International Relations',
    'Select Committee on Security and Justice': 'NCOP Security and Justice',
    'Portfolio Committee on International Relations and Co-operation': 'International Relations',
    'Select Committee on Communications and Public Enterprises': 'NCOP Communications and Public Enterprise',
    'Portfolio Committee on Defence and Military Veterans': 'Defence and Military Veterans',
    'Portfolio Committee on Water Affairs and Sanitation': 'Water and Sanitation',
    'Portfolio Committee on Tourism': 'Tourism',
    'Joint Standing Committee on Defence': 'Defence',
    'Portfolio Committee on Human Settlements': 'Human Settlements',
    'Portfolio Committee on Co-operative Governance and Traditional Affairs': 'Cooperative Governance and Traditional Affairs',
    'Portfolio Committee on Arts and Culture': 'Arts and Culture',
    'Joint Standing SubCommittee on Intelligence': 'Joint Standing on Intelligence',
    'Portfolio Committee on Environmental Affairs': 'Environmental Affairs',
    'Portfolio Committee on Basic Education': 'Basic Education',
    'Portfolio Committee on Women in the Presidency': 'Women in The Presidency',
    'Portfolio Committee on Transport': 'Transport',
    'Portfolio Committee on Economic Development': 'Economic Development',
    'Portfolio Committee on Energy': 'Energy',
    'Select Committee on Economic Development': 'NCOP Economic and Business Development',
    'Standing Committee on Appropriations': 'Standing Committee on Appropriations',
    'Select Committee on Land and Mineral Resources': 'NCOP Land and Mineral Resources',
    'Select Committee on Social Services': 'NCOP Social Services',
    'Portfolio Committee on Public Enterprises': 'Public Enterprises',
    'Portfolio Committee on Science and Technology': 'Science and Technology',
    'Select Committee on Education and Recreation': 'NCOP Education and Recreation',
    'Select Committee on Finance': 'NCOP Finance',
    'Joint Committee on Ethics and Members\' Interests': 'Ethics and Members\' Interest',
    'Joint Committee on Constitutional Review': 'Constitutional Review Committee',
    'Adhoc Commitee on violence against foreign nationals': 'Ad Hoc Joint Committee on Probing Violence Against Foreign Nationals',
    'Joint Subcommitteeon Review of the Joint Rules': 'Joint Rules',
    'Adhoc Committee on Police minister\'s Report on Nkandla': 'Ad Hoc Committee on Police Minister\'s Report on Nkandla ',
}

missing_committees = [
    'Multiparty Women\'s Caucus',
    'Subcommittee on Communications',
    'Subcommittee on Review of the Assembly Rules',
]


def log_error(writer, row, error=None):
    row['error'] = error
    writer.writerow([
        row['Column'], row['AET'], row['AST'], row['Date'],
        row['House'], row['ISSID'], row['Name Committee'],
        row['OST'], row['PMG Name'], row['alt'], row['attendance'],
        row['chairperson'], row['first_name'], row['party_affiliation'],
        row['province'], row['surname'], row['title'], row['error']
    ])


def get_member(members, initials, last_name, title):
    member_name = "%s, %s %s" % (last_name, title, initials)
    if member_name in missing_members:
        return None
    if member_name in member_name_map:
        return Member.query.filter(Member.name == member_name_map[member_name]).first()
    else:
        return Member.find_by_inexact_name(initials, last_name, title, members=members)

def get_committee(committee_name):
    if committee_name in missing_committees:
        return None
    return Committee.query.filter(Committee.name == committee_name_map[committee_name]).first()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Import Committee meeting attendance csv file')
    parser.add_argument('input', help='Path of file to import')
    parser.add_argument('log', help='Path of file to log errors')
    args = parser.parse_args()

    meeting_count = defaultdict(list)
    with open(args.input) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # This is used for checking multiple committee meetings in a single day
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

            existing_attendance = CommitteeMeetingAttendance.query.all()
            attendance_check = [(att.meeting_id, att.member_id) for att in existing_attendance]

            member_dict = {}
            committee_dict = {}
            committee_meeting_dict = {}
            meeting_attendance = []

            for row in reader:
                # Use this to limit the lines which are imported when testing.
                if reader.line_num >= 0:
                    if len(meeting_count[(row['Date'], row['Name Committee'])]) > 1:
                        # Check if multiple instances of meeting exist in import data.
                        # Committee name and date used to identify committee meetings
                        error = "Multiple committee meetings in a day found in import data."
                        log_error(writer, row, error=error)
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
                    initials = ""
                    for name in first_name.split():
                        initials += name[0]
                    member_name = "%s, %s %s" % (last_name, title, initials)

                    if member_name in member_dict:
                        member = member_dict[member_name]
                    else:
                        member = get_member(members, initials, last_name, title)

                    if not member:
                        # Member not found
                        log_error(writer, row, error='Member not found.')
                        print("Member not found: %s" % (str(reader.line_num)))
                        continue

                    # Get committee
                    committee_name = row['Name Committee']
                    if committee_name in committee_dict:
                        committee = committee_dict[committee_name]
                    else:
                        committee = get_committee(committee_name)
                        committee_dict[committee_name] = committee

                    # Get the committee meeting results
                    if committee:
                        if (committee.name, meeting_date.date()) in committee_meeting_dict:
                            committee_meeting_results = committee_meeting_dict[(committee.name, meeting_date.date())]
                        else:
                            committee_meeting_results = CommitteeMeeting.query\
                                .filter(CommitteeMeeting.committee == committee)\
                                .filter(func.date(CommitteeMeeting.date) == meeting_date.date())\
                                .all()
                            committee_meeting_dict[(committee.name, meeting_date.date())] = committee_meeting_results
                    else:
                        committee_meeting_results = []

                    if len(committee_meeting_results) != 1:
                        if committee == None:
                            error = "Committee not found"
                        elif len(committee_meeting_results) == 0:
                            error = "Committee meeting not found."
                        elif len(committee_meeting_results) > 1:
                            error = "Multiple committee meetings for date found in database."

                        log_error(writer, row, error=error)
                        print("Meeting error: %s :: No of meetings: %s" % (
                            str(reader.line_num), str(len(committee_meeting_results))))
                    else:
                        committee_meeting = committee_meeting_results[0]

                        if not (committee_meeting.id, member.id) in meeting_attendance:

                            meeting_attendance.append((committee_meeting.id, member.id))

                            committee_meeting.date = meeting_date
                            committee_meeting.actual_start_time = ast
                            committee_meeting.actual_end_time = aet

                            if (committee_meeting.id, member.id) not in attendance_check:
                                committee_meeting_attendance = CommitteeMeetingAttendance(
                                    alternate_member=alternate_member,
                                    attendance=attendance,
                                    chairperson=chairperson,
                                    meeting=committee_meeting,
                                    member=member)

                                db.session.add(committee_meeting_attendance)
                                print('Adding attendance: %s' % (reader.line_num))
                            else:
                                print('Attendance exists: %s' % (reader.line_num))

                        else:
                            log_error(writer, row, error='Duplicate attendance for meeting in sheet.')
                            continue

                    if reader.line_num % 100 == 0:
                        db.session.flush()
            db.session.flush()
            # db.session.commit()
