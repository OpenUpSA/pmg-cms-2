import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert csv file into correct format')
    parser.add_argument('input', help='Path of file to fix')
    parser.add_argument('log', help='Path of file to write correct format to')
    args = parser.parse_args()

    with open(args.log, 'wb') as outputfile:
        with open(args.input) as inputfile:
            writer = csv.writer(outputfile)
            reader = csv.DictReader(inputfile)

            # for field in reader.fieldnames:
            #     field = field.strip()

            writer.writerow([
                'Column', 'AET', 'AST', 'Date',
                'House', 'ISSID', 'Name Committee',
                'OST', 'PMG Name',
                'alt', 'attendance', 'chairperson',
                'first_name', 'party_affiliation',
                'province', 'surname', 'title'])

            for row in reader:
                # Clean field names
                for key in row.iterkeys():
                    new_key = key.strip(' \t\n\r')
                    row[new_key] = row.pop(key)

                col = reader.line_num
                aet = row['AET']
                ast = row['AST']
                date = row['Date']
                house = row['House']
                issid = row['ISSID']
                committee = row['Name Committee']
                ost = row['OST']
                pmg = row['PMG Name']
                alt = None
                chair = 'TRUE'
                province = None

                # Write chairperson
                writer.writerow([
                    col, aet, ast, date, house, issid, committee, ost, pmg,
                    alt, row['Attendance Chair'], chair, row['First Name Chairperson'],
                    row['Party Affiliation Chairperson'], province,
                    row['Surname Chairperson'], row['Title Chairperson']
                ])

                chair = 'FALSE'
                for i in range(1, 35):
                    i = str(i)
                    if row['Attendance Member ' + i]:
                        try:
                            writer.writerow([
                                col, aet, ast, date, house, issid, committee, ost, pmg,
                                row['Alt (Y or N) Member ' + i], row['Attendance Member ' + i], chair, row['First Name Member ' + i],
                                row['Party Affiliation Member ' + i], province,
                                row['Surname Member ' + i], row['Title Member ' + i]
                            ])
                        except KeyError as e:
                            import ipdb; ipdb.set_trace()
                            print e

