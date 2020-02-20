#!/usr/bin/env python
#
# A script to count the number of parliamentary days between two dates.
# Input file is like:
#
# introduction, adoption
# 2018-01-01, 2018-03-02

import argparse
import os.path
import sys
import csv
from datetime import date

from pmg.bills import count_parliamentary_days


def str_to_date(d):
    return date(*(int(x) for x in d.split("-")))


def calc_pm_days(args):
    with open(args.csv) as f:
        reader = csv.reader(f, delimiter=",")
        writer = csv.writer(sys.stdout)

        for i, row in enumerate(reader):
            if i == 0:
                writer.writerow([row[0], row[1], "pm_days"])
                continue

            if row[0] and row[1]:
                intro, adopt = (str_to_date(x) for x in row[:2])
                pm_days = count_parliamentary_days(intro, adopt)
            else:
                pm_days = ""

            writer.writerow([row[0], row[1], pm_days])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate how many of the days that passed between the stages of bills, were parliamentary days"
    )
    parser.add_argument(
        "--csv",
        metavar="csv-file",
        help="A CSV file with two columns, the date of introduction and the date of adoption.",
        required=True,
    )

    args = parser.parse_args()
    calc_pm_days(args)
