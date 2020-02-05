#!/usr/bin/env python
#
# A script to load the parliament days into PMG.
# Requires an Excel file indicating which days were Parliamentary days with a 'P'.
#
#   PARLIAMENT SITTING DAYS
#   2015 | 1 | 2 | 3 | ...
#   JAN  |   |   | P | ...
#   FEB  |   | P | P | ...
#   ...
#

from builtins import str
from builtins import range
import argparse
import os.path
from datetime import date
from xlrd import open_workbook


def build_pm_dates(pm_days_file):
    # Run through the document,
    # and return a list of days which were parliamentary days

    book = open_workbook(pm_days_file, on_demand=True)
    dates = list()

    for sheet in book.sheets():
        year = int(sheet.cell_value(1, 0))
        for row in range(2, sheet.nrows):
            # Check for empty values as some sheets contain other
            # bits of information beyond the rows of the calendar.
            if sheet.cell_type(row, 0) != 0:
                for col in range(1, sheet.ncols):
                    if sheet.cell_value(row, col) == "P":
                        try:
                            dates.append(date(year, row - 1, col))
                        except ValueError:
                            # Date doesn't exist e.g. 30 Feb
                            # Ignore the cell, and move along
                            continue

    return dates


def load_parliamentary_days(args):
    dates = sorted(build_pm_dates(args.pm_days))

    with open(
        os.path.join(os.path.dirname(__file__), "../data/parliament-sitting-days.txt"),
        "w",
    ) as f:
        for d in dates:
            f.write(str(d))
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate how many of the days that passed between the stages of bills, were parliamentary days"
    )
    parser.add_argument(
        "--pm-days",
        metavar="excel-file",
        help="An Excel document containing sheets that indicate which days of the year were parliamentary days",
        required=True,
    )

    args = parser.parse_args()
    load_parliamentary_days(args)
