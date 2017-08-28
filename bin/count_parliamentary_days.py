#!/bin/env python
#
# A script to calculate how many parliamentary days have passed between the
# different stages of bills being passed through parliament.
#
# Requires an Excel file indicating which days were Parliamentary days,
# and a file showing the dates between the various stages of the bills.
#

import argparse
import csv
from datetime import datetime
from xlrd import open_workbook, xldate


CSV_HEADERS = [
    'ID',
    'Date of introduction',
    'Date of adoption',
    'PM days to adoption'
]

def build_pm_day_calendar(pm_days):
    # Run through the document,
    # and return a list of days which were parliamentary days

    book = open_workbook(pm_days, on_demand=True)
    pm_day_calendar = list()

    for sheet in book.sheets():
        year = int(sheet.cell_value(1, 0))
        for row in range(2, sheet.nrows):
            # Check for empty values as some sheets contain other
            # bits of information beyond the rows of the calendar.
            if sheet.cell_type(row, 0) != 0:
                for col in range(1, sheet.ncols):
                    if sheet.cell_value(row, col) == 'P':
                        try:
                            date = datetime(year, row-1, col)
                            pm_day_calendar.append(date)
                        except ValueError:
                            # Date doesn't exist e.g. 30 Feb
                            # Ignore the cell, and move along
                            continue

    return pm_day_calendar


def count_pm_days(event, pm_day_calendar):
    for day in pm_day_calendar:
        if event['dates']['intro_date'] < day <= event['dates']['adoption_date']:
            event['pm_days']['days_to_adoption'] += 1


def get_bill_event_pm_days(bill_events_file, pm_day_calendar):
    book = open_workbook(bill_events_file, on_demand=True)
    sheet = book.sheet_by_name('Results')

    bill_events = []
    for row in range(1, sheet.nrows):
        # There may be extra rows in the sheet, like totals or averages
        # so check for empty values in the first column.
        if sheet.cell_type(row, 0) != 0:

            bill_events.append({
                    "id": int(sheet.cell_value(row, 0)),
                    "xl_dates": {
                        "intro_date": sheet.cell(row, 6),
                        "adoption_date": sheet.cell(row, 7),
                    },
                    "dates": {},
                    "pm_days": {
                        'days_to_adoption': 0,
                    }
                })

    for event in bill_events:
        for event_name, date in event['xl_dates'].iteritems():
            if date.ctype == 1:
                # Date in cell is plain text
                event['dates'][event_name] = datetime(
                    int(date.value[0:4]),
                    int(date.value[5:7]),
                    int(date.value[8:10]))

            elif date.ctype == 3:
                # Date in cell was converted to a float when read
                fmt_date = xldate.xldate_as_tuple(date.value, 0)
                event['dates'][event_name] = datetime(fmt_date[0], fmt_date[1], fmt_date[2])

        count_pm_days(event, pm_day_calendar)

    return bill_events


def write_to_csv(bill_event_pm_days):
    with open('bill_event_pm_days.csv', 'wb') as results_file:
        writer = csv.writer(results_file)
        writer.writerow(CSV_HEADERS)
        for event in bill_event_pm_days:
            writer.writerow([
                event['id'],
                event['dates']['intro_date'].date(),
                event['dates']['adoption_date'].date(),
                event['pm_days']['days_to_adoption']]
            )


def parliamentary_days_to_csv(args):
    pm_day_calendar = build_pm_day_calendar(args.pm_days)
    bill_event_pm_days = get_bill_event_pm_days(args.bill_events, pm_day_calendar)
    write_to_csv(bill_event_pm_days)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate how many of the days that passed between the stages of bills, were parliamentary days')
    parser.add_argument('--pm-days', metavar="Excel Sheet", help='An Excel document containing sheets that indicate which days of the year were parliamentary days', required=True)
    parser.add_argument('--bill-events', metavar="Excel Sheet", help='An Excel document containing a sheet with dates of the various stages of bills', required=True)

    args = parser.parse_args()
    parliamentary_days_to_csv(args)
