#!/bin/env python

import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Member

member_name_map = {
    "Mandela, Mr Z": "Mandela, Nkosi ZM",
    "Mthethwa, Mr E": "Mthethwa, Mr EM",
    "Michael, Ms N": "Mazzone, Ms NW",
    "Van Der Merwe, Mr J": "Van der Merwe, Mr JH",
    "Mpheti, Mr S": "Mphethi, Mr SSA",
    "Mmola, Ms M": "MMola, Ms MP",
    "Kohler, Ms D": "Kohler-Barnard, Ms D",
    "Pilane-majake, Ms M": "Pilane-Majake, Ms MC",
    "Litchfield-tshabalala, Ms K": "Litchfield-Tshabalala, Ms K",
    "Madikizela-mandela, Ms N": "Madikizela-Mandela, Ms NW",
    "Van Der Merwe, Ms L": "van der Merwe, Ms LL",
    "Ngwenya-mabila, Ms P": "Ngwenya-Mabila, Ms PC",
    "Moloi-moropa, Ms J": "Moloi-Moropa, Ms JC",
    "Hill-lewis, Mr G": "Hill-Lewis, Mr GG",
    "Mpambo-sibhukwana, Ms T": "Mpambo-Sibhukwana, Ms T",
    "Ramokhoase, Mr T": "Ramokhoase , Mr TR",
    "Luzipo, Mr S": "Luzipho, Mr S",
    "Pilane-majake, Ms C": "Pilane-Majake, Ms MC",
    "Dlamini-dubazana, Ms Z": "Dlamini-Dubazana, Ms ZS",
    "Mc Gluwa, Mr J": "McGluwa, Mr JJ",
    "Van Der Westhuizen, Mr A": "van der Westhuizen, Mr AP",
    "Mente-nqweniso, Ms N": "Mente-Nqweniso, Ms NV",
    "Scheepers, Ms M": "Scheepers, Ms MA",
    "Faber, Mr W": "Faber, Mr WF",
    "Makhubela-mashele, Ms L": "Makhubela-Mashele, Ms LS",
    "Xego-sovita, Ms S": "Xego, Ms ST",
    "Mnganga - Gcabashe, Ms L": "Mnganga-Gcabashe, Ms LA",
    "Bam-mugwanya, Ms V": "Bam-Mugwanya, Ms V",
    "Steenkamp, Ms J": "Edwards, Ms J",
    "Tarabella Marchesi, Ms N": "Tarabella - Marchesi, Ms NI",
    "Shope-sithole, Ms S": "Shope-Sithole, Ms SC",
    "Mcloughlin, Mr A": "McLoughlin, Mr AR",
    "Letsatsi-duba, Ms D": "Letsatsi-Duba, Ms DB",
    "Kekana, Mr HB": "Kekana, Ms HB",
    "Faber, Mr W": "Faber, Mr WF",
    "Scheepers, Ms M": "Scheepers Ms MA",
}


def get_member(members, initials, last_name, title):
    member_name = "%s, %s %s" % (last_name, title, first_name[0])

    if member_name == "Faber, Mr W":
        import ipdb

        ipdb.set_trace()

    if member_name in member_name_map:
        return Member.query.filter(Member.name == member_name_map[member_name]).first()
    else:
        return Member.find_by_inexact_name(initials, last_name, title, members=members)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Check if members are matched correctly."
    )
    parser.add_argument("input", help="Path of file to check")
    args = parser.parse_args()

    with open(args.input) as csvfile:

        reader = csv.DictReader(csvfile)

        members = Member.query.all()
        member_dict = {}

        for row in reader:
            first_name = row["first_name"]
            last_name = row["surname"]
            title = row["title"]
            initials = ""
            for name in first_name.split():
                initials += name[0]

            member_name = "%s, %s %s" % (last_name, title, initials)

            if member_name not in member_dict:
                # Else already logged
                member = get_member(members, initials, last_name, title)
                member_dict[member_name] = member

                if not member:
                    # Member not found
                    print("%s: Not found" % (member_name))

                elif member_name != member.name:
                    print("'%s': '%s'," % (member_name, member.name))

            continue
