#!/bin/env python

from pmg.models import Bill, BillVersion, File, db, BillType
import json
import re

bills = json.load(open('data/bills-with-files.json'))
bill_pages = json.load(open('data/bill-pages.json'))
nids = json.load(open('data/nid_url.json'))

pages_by_nid = {p["nid"]: p for p in bill_pages}
nids_by_url = {n["url"]: n for n in nids}
nids = {n["nid"]: n for n in nids}

DESC_RE = re.compile('s:\d+:"description";s:\d+:"([^"]*)";')


def get_description(s):
    # u'a:11:{s:11:"description";s:31:"Division of Revenue Act 10-2014";s:3:"fid";s:5:"51280";s:5:"width";i:0;s:6:"height";i:0;s:8:"duration";i:0;s:12:"audio_format";s:0:"";s:17:"audio_sample_rate";i:0;s:18:"audio_channel_mode";s:0:"";s:13:"audio_bitrate";i:0;s:18:"audio_bitrate_mode";s:0:"";s:4:"tags";a:0:{}}'
    match = DESC_RE.search(s)
    if match:
        return match.group(1)


def get_file_info(url):
    url = url.replace('http://www.pmg.org.za/', '')

    if url.startswith('node/'):
        nid = nids[url[5:]]["nid"]
    else:
        nid = nids_by_url.get(url)
        if nid:
            nid = nid["nid"]
        else:
            nid = {
                u'bill/20060425-south-african-institute-for-drug-free-sport-amendment-act-25-2006': "44724",
            }[url]

    page = pages_by_nid[nid]
    files = page["files"]
    f = files[0]

    f['description'] = get_description(f['field_file_bill_data'])
    if f['filepath'].startswith('files/'):
        f['filepath'] = f['filepath'][6:]

    return f


added = 0
missing = 0
already_enacted = 0
already_exists = 0

def commit():
    #db.session.commit()
    print "added %d" % added
    print "missing %d" % missing
    print "already_enacted %d" % already_enacted
    print "already_exists %d" % already_exists

# now load files into db
not_found = []
for bill in bills:
    year = bill['year']
    number = bill['number']
    title = bill['name']
    bill_type = bill['bill_type']

    bill_obj = Bill.query.filter(Bill.year == year, Bill.number == number).join(BillType).filter(BillType.name == bill_type).first()
    if not bill_obj:
        print "Missing: %s %s -- %s" % (year, number, title)
        missing += 1
        continue

    print "%s %s %s -- %s" % (bill_obj.id, year, number, title)

    # already have enacted?
    if any(v.enacted for v in bill_obj.versions):
        already_enacted += 1
        print "Already have enacted, skipping"
        continue

    for version in (e for e in bill['entries'] if e['type'] == 'act'):
        # find the file details
        info = get_file_info(version["url"])
        print "Version info: %s" % version
        print "File info: %s" % info

        # is there already a matching version?
        existing = [bv for bv in bill_obj.versions if bv.file.file_path == info['filepath']]
        if existing:
            existing[0].enacted = True
            already_exists += 1
            print "Already have matching file, skipping"
            continue

        # does the file exist?
        file = File.query.filter(File.file_path == info['filepath']).first()
        if not file:
            raise ValueError("File %s doesn't exist" % info['filepath'])

        if not file.title:
            file.title = info['description']

        date = version['date']
        # if no date, use the date it was signed
        if not date or date == 'None':
            events = [e for e in bill_obj.events if e.type == 'bill-signed']
            events.sort(key=lambda e: e.date, reverse=True)
            date = events[0].date

        bill_version = BillVersion()
        bill_version.date = date
        bill_version.title = version['title']
        bill_version.file = file
        bill_version.enacted = True
        bill_version.bill = bill_obj
        added += 1
        db.session.add(bill_version)
        db.session.flush()

        if added % 10 == 0:
            commit()

commit()
