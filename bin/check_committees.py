#!/bin/env python

from __future__ import print_function
import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Committee, House

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


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Check if members are matched correctly.')
    parser.add_argument('input', help='Path of file to check')
    args = parser.parse_args()

    with open(args.input) as csvfile:
        reader = csv.DictReader(csvfile)

        all_committees = Committee.query.all()
        na_committees = Committee.query.filter(House.name_short == 'NA').all()
        ncop_committees = Committee.query.filter(House.name_short == 'NCOP').all()

        committee_dict = {}

        for row in reader:
            if reader.line_num >= 0:
                if row['Name Committee'] not in committee_dict:
                    # Else already logged
                    committee_name = row['Name Committee']
                    if committee_name in committee_name_map:
                        committee = Committee.query.filter(Committee.name == committee_name_map[committee_name]).first()

                    elif row['House'] == 'NA':
                        if 'Portfolio Committee on' in committee_name:
                            committee_name = committee_name[len('Portfolio Committee on')+1:]
                        committee = Committee.find_by_inexact_name(committee_name, candidates=na_committees)

                    elif row['House'] == 'NCOP':
                        if 'Select Committee on' in committee_name:
                            committee_name = committee_name[len('Select Committee on')+1:]
                        committee = Committee.find_by_inexact_name(committee_name, candidates=ncop_committees)

                    else:
                        committee = Committee.find_by_inexact_name(committee_name, candidates=all_committees)

                    committee_dict[row['Name Committee']] = committee

                    if not committee:
                        # Committee not found
                        print("%s: Not found" % (row['Name Committee']))

                    else:
                        print("'%s': '%s'," % (row['Name Committee'], committee.name))

                continue
