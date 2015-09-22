#!/bin/env python

import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Committee, House

member_name_map = {
    'Kohler, Ms D': 'Kohler-Barnard, Ms D',
    'Michael, Ms N': 'Mazzone, Ms NW',
    'Steenkamp, Ms J': 'Edwards, Ms J'
}

committee_name_map = {
    'Standing Committee on Finance': 'Finance Standing Committee',
    'Finance': 'NCOP Finance',
    'Economic Development': 'NCOP Economic and Business Development',
    'Appropriations': 'NCOP Appropriations',
    'Social Services': 'NCOP Social Services',
    'Ad hoc Committee on Powers and Privileges  of Parlaiment': 'Powers and Privileges',
    'Public Services and Administration': 'Public Service and Administration, as well as Performance Monitoring and Evaluation',
    'Joint Standing Committee on Defence': 'Defence',
    'Ad Hoc Committee on Open Democracy Bill': 'Promotion of Access to Information Bill (Open Democracy Bill)',
    'Ad Hoc Committee Nkandla': 'Ad Hoc Committee - President\'s Submission in response to Public Protector\'s Report on Nkandla',
    'Standing Committee on Public Accounts': 'Public Accounts',
    'Subcommittee on Review of the Assembly Rules': 'Rules of the National Assembly',
    'the Review of the National Assembly Rules': 'Rules of the National Assembly',
    'International Relations and Co-operation': 'International Relations',
    'Joint Committee on Ethics and Members\' Interests': 'Ethics and Members\' Interest',
    'Joint Committee on Constitutional Review': 'Constitutional Review Committee',
    'Joint Subcommitteeon Review of the Joint Rules': 'Joint Rules',
}

def log_error(writer, committee_name, matched_name=None, error=None):
    writer.writerow([
        committee_name, matched_name, error
    ])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Check if members are matched correctly.')
    parser.add_argument('input', help='Path of file to check')
    parser.add_argument('log', help='Path of file to log mismatches')
    args = parser.parse_args()

    with open(args.log, 'wb') as logfile:
        with open(args.input) as csvfile:

            writer = csv.writer(logfile)
            reader = csv.DictReader(csvfile)

            all_committees = Committee.query.all()
            ncop_committees = Committee.query.filter(House.name_short == 'NCOP')

            committee_dict = {}

            for row in reader:
                committee_name = row['Name Committee']
                select_committee = False

                if 'Portfolio Committee on' in committee_name:
                    # Remove from committee_name as it doesn't appear in the db
                    committee_name = committee_name[len('Portfolio Committee on')+1:]
                elif 'Select Committee on' in committee_name:
                    select_committee = True
                    committee_name = committee_name[len('Select Committee on')+1:]

                if committee_name not in committee_dict:
                    # Else already logged
                    if committee_name in committee_name_map:
                        committee = Committee.query.filter(Committee.name == committee_name_map[committee_name]).first()
                    elif select_committee:
                        committee = Committee.find_by_inexact_name(committee_name, candidates=ncop_committees)
                    else:
                        committee = Committee.find_by_inexact_name(committee_name, candidates=all_committees)
                    committee_dict[committee_name] = committee

                    if not committee:
                        # Committee not found
                        log_error(writer, committee_name, error='Committee not found.')

                    elif committee_name != committee.name:
                        log_error(writer, committee_name, matched_name=committee.name)

                continue
