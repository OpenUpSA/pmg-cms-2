from pmg.models import Bill, BillVersion, File, db
import json

bills = json.load(open('bills-with-files.json'))


# now load files into db
not_found = []
for bill in bills:
    year = bill['year']
    number = bill['number']
    title = bill['name']

    for version in (e for e in bill['entries'] if e['type'] == 'act' and e['file']):
        bill = Bill.query.filter(Bill.year == year, Bill.number == number, Bill.title == title).first()
        if not bill:
            print "Missing: %s %s -- %s" % (year, number, title)
            continue

        print "%s %s %s -- %s" % (bill.id, year, number, title)

        info = version['file']

        file = File()
        file.file_mime = info['filemime']
        file.origname = info['origname']
        file.file_path = info['filepath']

        bill_version = BillVersion()
        bill_version.date = info['date']
        bill_version.title = info['title']
        bill_version.file = file
        1/0

db.session.commit()
