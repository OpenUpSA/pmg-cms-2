#!/bin/env python

import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Member

member_name_map = {
    'Mandela, Mr Z': 'Mandela, Nkosi ZM',
    'Kohler, Ms D': 'Kohler-Barnard, Ms D',
    'Mthethwa, Mr E': 'Mthethwa, Mr EM',
    'Michael, Ms N': 'Mazzone, Ms NW',
    'Steenkamp, Ms J': 'Edwards, Ms J'
}

def log_error(writer, member_name, matched_name=None, error=None):
    writer.writerow([
        member_name, matched_name, error
    ])

def get_member(members, first_name, last_name, title):
    member_name = "%s, %s %s" % (last_name, title, first_name[0])

    if member_name in member_name_map:
        return Member.query.filter(Member.name == member_name_map[member_name]).first()
    else:
        return Member.find_by_inexact_name(first_name, last_name, title, members=members)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Check if members are matched correctly.')
    parser.add_argument('input', help='Path of file to check')
    parser.add_argument('log', help='Path of file to log mismatches')
    args = parser.parse_args()

    with open(args.log, 'wb') as logfile:
        with open(args.input) as csvfile:

            writer = csv.writer(logfile)
            reader = csv.DictReader(csvfile)

            members = Member.query.all()
            member_dict = {}

            for row in reader:
                first_name = row['first_name']
                last_name = row['surname']
                title = row['title']
                member_name = "%s, %s %s" % (last_name, title, first_name[0])

                if member_name not in member_dict:
                    # Else already logged
                    member = get_member(members, first_name, last_name, title)
                    member_dict[member_name] = member

                    if not member:
                        # Member not found
                        log_error(writer, member_name, error='Member not found.')

                    elif member_name[0:member_name.find(',')] != member.name[0:member.name.find(',')]:
                        log_error(writer, member_name, matched_name=member.name)

                continue
