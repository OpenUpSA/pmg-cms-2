import os
import json
import time, datetime
import parsers
import logging
import csv
import re

import requests
from sqlalchemy import types

from backend.app import app, db
from backend.models import *
from backend.search import Search

logger = logging.getLogger('rebuild_db')
logging.getLogger('sqlalchemy.engine').level = logging.WARN

STATIC_HOST = app.config['STATIC_HOST']
db.echo = False

def strip_filepath(filepath):

    return "/".join(filepath.split("/")[1::])


def dump_db(name):
    try:
        os.remove(name)
    except Exception as e:
        logger.debug(e)
        pass
    return


def read_data(filename):
    start = time.time()

    logger.debug("reading " + filename)
    with open('data/' + filename, 'r') as f:
        records = []
        lines = f.readlines()
        for line in lines:
            records.append(json.loads(line))
    return records

def db_date_from_utime(utime):
    try:
        return datetime.datetime.fromtimestamp(float(utime))
    except:
        try:
            datetime.strptime(utime, '%Y-%m-%dT%H:%m:%s')
        except:
            return None

def construct_obj(obj, mappings):
    """
    Returns a result with the properties mapped by mapping, including all revisions
    """
    result_obj = {}
    # print obj
    for key in mappings.keys():
        if (obj.has_key(key)):
            result_obj[key] = obj[key]
    if (obj.has_key("revisions") and (type(obj["revisions"]) is list) and (len(obj["revisions"]) > 0)):
        for revision in obj["revisions"]:
            tmp = construct_obj(revision, mappings)
            result_obj.update(tmp)
    return result_obj

def find_files(obj):
    files = []
    if (obj.has_key("files") and (type(obj["files"]) is list) and (len(obj["files"]) > 0)):
        # print obj["files"]
        for f in obj["files"]:
            fobj = File(
                filemime=f["filemime"],
                origname = f["origname"],
                url = f["filepath"].replace("files/", ""),
                )
            db.session.add(fobj)
            files.append(fobj)
        db.session.commit()
    if (obj.has_key("audio") and (type(obj["audio"]) is list) and (len(obj["audio"]) > 0)):
        # print obj["audio"]
        for f in obj["audio"]:
            fobj = File(
                filemime=f["filemime"],
                origname = f["origname"],
                url = "audio/" + f["filename"].replace("files/", ""),
                playtime = f["playtime"],
                description = f["title_format"]
            )
            db.session.add(fobj)
            files.append(fobj)
        db.session.commit()
    return files

def find_committee(obj):
    committees = []
    if (obj.has_key("terms") and (type(obj["terms"]) is list) and (len(obj["terms"]) > 0)):
        # print obj["terms"]
        for term in obj["terms"]:
            committee = Committee.query.filter_by(name = term).first()
            # print committee, term
            if committee:
                committees.append(committee)
                # else:
                #     print term
    return committees

def prep_table(model_class):
    print "Deleted rows: ", model_class.query.delete()


def rebuild_table(table_name, model_class, mappings):
    logger.debug("Rebuilding %s" % table_name)
    prep_table(model_class)
    i = 0
    with open('data/' + table_name + '.json', 'r') as f:
        lines = f.readlines()
        logger.debug("Found %i records" % (len(lines)))
        for line in lines:
            try:
                obj = json.loads(line)
                newobj = construct_obj(obj, mappings)
                # Check for Dates
                for mapping in mappings.keys():
                    row_type = getattr(model_class, mapping).property.columns[0].type
                    if (row_type.__str__() == "DATE"):
                        if (newobj.has_key(mappings[mapping])):
                            newobj[mappings[mapping]] = db_date_from_utime(newobj[mappings[mapping]])
                new_rec = model_class()
                files = find_files(obj)
                committees = find_committee(obj)
                if hasattr(new_rec, 'committee_id'):
                    if len(committees):
                        new_rec.committee_id = committees[0].id
                else:
                    if (committees):
                        for committee in committees:
                            new_rec.committee.append(committee)
                if (len(files)):
                    for f in files:
                        new_rec.files.append(f)
                for key,val in newobj.iteritems():
                    setattr(new_rec, key, val)
                db.session.add(new_rec)
                i += 1
                if (i == 100):
                    db.session.commit()
                    i = 0
                    logger.debug("Wrote 100 rows...")
            except:
                logger.warning("Error reading row for " + table_name)
        db.session.commit()

def guess_pa_link(name, names):
    name_parts = re.split(",", name)
    first_letter = None
    surname = name_parts[0]
    if (len(name_parts) > 1):
        name_parts = re.split(" ", name_parts[1].strip())
        if (len(name_parts) > 1 and len(name_parts[1])):
            first_letter = name_parts[1][0]
    for pa_name in names:
        # print pa_name[1], surname
        if surname in pa_name[1].decode("utf-8"):
            if first_letter and first_letter is pa_name[1].decode("utf-8")[0]:
                return pa_name[0]
    return None

def rebuild_db():
    """
    Save json fixtures into a structured database, intended for use in our app.
    """

    start = time.time()

    # populate houses of parliament
    joint_obj = House(name="Joint (NA + NCOP)", name_short="Joint")
    ncop_obj = House(name="National Council of Provinces", name_short="NCOP")
    na_obj = House(name="National Assembly", name_short="NA")
    for obj in [joint_obj, ncop_obj, na_obj]:
        db.session.add(obj)
    db.session.commit()

    # populate membership_type
    chairperson = MembershipType(name="chairperson")
    db.session.add(chairperson)
    db.session.commit()

    # populate bill_type options
    tmp = [
        ('X', 'Draft', 'Draft'),
        ('B', 'S74', 'Section 74: Constitutional amendments'),
        ('B', 'S75', 'Section 75: Ordinary Bills not affecting the provinces'),
        ('B', 'S76', 'Section 76: Ordinary Bills affecting the provinces'),
        ('B', 'S77', 'Section 77: Money Bills'),
        ('PMB', 'Private Member Bill',
         'Private Member Bill: Bills that are drawn up by private members, as opposed to ministers or committees.')
        ]
    for (prefix, name, description) in tmp:
        bill_type = BillType(prefix=prefix, name=name, description=description)
        db.session.add(bill_type)
    db.session.commit()

    # populate bill_status options
    tmp = [
        ('lapsed', 'Lapsed'),
        ('withdrawn', 'Withdrawn'),
        ('na', 'Under consideration by the National Assembly.'),
        ('ncop', 'Under consideration by the National Council of Provinces.'),
        ('president', 'Approved by parliament. Waiting to be signed into law.'),
        ('enacted', 'The bill has been signed into law.'),
        ('act-commenced', 'Act commenced'),
        ('act-partly-commenced', 'Act partially commenced'),
        ]
    for (name, description) in tmp:
        bill_status = BillStatus(name=name, description=description)
        db.session.add(bill_status)
    db.session.commit()

    # populate committees
    committees = {}
    committee_list = read_data('comm_info_page.json')
    for committee in committee_list:
        if committee['terms']:
            name = committee['terms'][0].strip()
            if name not in committees.keys():
                committees[name] = {}
            committee_obj = construct_obj(committee, { "comm_info_type": "comm_info_type", "body": "body" })
            # logger.debug(committee_obj)
            if committee_obj.has_key("comm_info_type"):
                if committee_obj["comm_info_type"] == 'About':
                    committees[name]["about"] = committee_obj["body"]
                elif committee_obj["comm_info_type"] == 'Contact':
                    committees[name]["contact"] = committee_obj["body"]
    for key, val in committees.iteritems():
        # logger.debug(val)
        committee = Committee()
        committee.name = key

        # set parent relation
        if "ncop" in committee.name.lower():
            committee.house_id = ncop_obj.id
        elif "joint" in committee.name.lower():
            committee.house_id = joint_obj.id
        else:
            committee.house_id = na_obj.id

        # committee_info = CommitteeInfo()
        if val.get("about"):
            committee.about = val["about"]
        if val.get("contact"):
            committee.contact_details = val["contact"]

        db.session.add(committee)
        val['model'] = committee
    db.session.commit()

    # populate committee members
    pa_members = []
    with open('./scrapers/members.csv', 'r') as csvfile:
        membersreader = csv.reader(csvfile)
        for row in membersreader:
            pa_members.append(row)

    members = read_data('committee_member.json')
    for member in members:
        member_obj = Member(
            name=member['title'].strip(),
            start_date = db_date_from_utime(member['start_date']),
            pa_link = guess_pa_link(member['title'].strip(), pa_members)
        )
        if member.get('files'):
            member_obj.profile_pic_url = strip_filepath(member["files"][-1]['filepath'])
        logger.debug(member_obj.name)
        logger.debug(member_obj.profile_pic_url)

        # extract bio info
        if member['revisions']:
            bio = member['revisions'][0]['body']
            if bio:
                index = bio.find("Further information will be provided shortly on:")
                if index and index > 0:
                    bio = bio[0:index].strip()
                    logger.debug(bio)
                    member_obj.bio = bio

        # set committee relationships
        for term in member['terms']:
            if committees.get(term):
                org_model = committees[term]['model']
                membership_obj = Membership(committee=org_model)
                member_obj.memberships.append(membership_obj)
            else:
                logger.debug("committee not found: " + term)

        # set party membership
        party = member['mp_party']
        if party:
            logger.debug(party)
            party_obj = Party.query.filter_by(name=party).first()
            if not party_obj:
                party_obj = Party(name=party)
                db.session.add(party_obj)
                db.session.commit()
            member_obj.party_id = party_obj.id

        # set house membership
        house = member['mp_province']
        if house == "National Assembly":
            member_obj.house_id = na_obj.id
        elif house and "NCOP" in house:
            member_obj.house_id = ncop_obj.id
            # logger.debug(house)
            province_obj = Province.query.filter_by(name=house[5::]).first()
            if not province_obj:
                province_obj = Province(name=house[5::])
                db.session.add(province_obj)
                db.session.commit()
            member_obj.province_id = province_obj.id

        db.session.add(member_obj)
        logger.debug('')
    db.session.commit()

    # select a random chairperson for each committee
    tmp_committees = Committee.query.all()
    for committee in tmp_committees:
        if committee.memberships:
            membership_obj = committee.memberships[0]
            membership_obj.type_id = 1
            db.session.add(membership_obj)
    db.session.commit()

    # populate committee reports
    i = 0
    db.session.commit()
    logger.debug("reading report.js")
    with open('data/report.json', 'r') as f:
        records = []
        lines = f.readlines()
        for line in lines:
            report = json.loads(line)
            parsed_report = parsers.MeetingReportParser(report)

            committee_obj = committees.get(parsed_report.committee)
            if committee_obj:
                committee_obj = committee_obj['model']

            event_obj = Event(
                type="committee-meeting",
                committee=committee_obj,
                date=parsed_report.date,
                title=parsed_report.title
            )
            db.session.add(event_obj)

            report_obj = CommitteeMeetingReport(
                body=parsed_report.body,
                summary=parsed_report.summary,
                event=event_obj
            )
            db.session.add(report_obj)

            for item in parsed_report.related_docs:
                doc_obj = Content(
                    event=event_obj,
                    type=item["filemime"],
                    )
                doc_obj.file_path=item["filepath"]
                doc_obj.title=item["title"]
                db.session.add(doc_obj)

            for item in parsed_report.audio:
                audio_obj = Content(
                    event=event_obj,
                    type=item["filemime"],
                    )
                if item["filepath"].startswith('files/'):
                    audio_obj.file_path=item["filepath"][6::]
                else:
                    audio_obj.file_path=item["filepath"]
                if item.get("title_format"):
                    audio_obj.title=item["title_format"]
                elif item.get("filename"):
                    audio_obj.title=item["filename"]
                elif item.get("origname"):
                    audio_obj.title=item["origname"]
                else:
                    audio_obj.title="Unnamed audio"
                db.session.add(audio_obj)

            i += 1
            if i % 500 == 0:
                logger.debug("writing 500 reports...")
                db.session.commit()
    return

def addChild(Child, val):
    if (val):
        tmpobj = Child.query.filter_by(name = val).first()
        if not tmpobj:
            tmpobj = Child(name=val)
            db.session.add(tmpobj)
            db.session.commit()
        return tmpobj.id
    return None

def bills():
    prep_table("bill")
    r = requests.get('http://billsapi.pmg.org.za/bill/')
    bills = r.json()
    for billobj in bills:
        bill = Bill()
        bill.title = billobj["name"]
        bill.bill_code = billobj["code"]
        # act_name = db.Column(db.String(250))
        bill.number = billobj["number"]
        bill.year = billobj["year"]
        # date_of_introduction = db.Column(db.Date)
        # date_of_assent = db.Column(db.Date)
        # effective_date = db.Column(db.Date)
        bill.objective = billobj["objective"]
        bill.is_deleted = billobj["is_deleted"]
        bill.status_id = addChild(BillStatus, billobj["status"])
        bill.type_id = addChild(BillType, billobj["bill_type"])
        # place_of_introduction_id = db.Column(db.Integer, db.ForeignKey('committee.id'))
        # place_of_introduction = db.relationship('Committee')
        # introduced_by_id = db.Column(db.Integer, db.ForeignKey('member.id'))
        # introduced_by = db.relationship('Member')
        db.session.add(bill)
    db.session.commit()

def add_featured():
    committeemeetings = CommitteeMeetingReport.query.limit(5)
    tabledreports = TabledCommitteeReport.query.limit(5)
    featured = Featured()
    for committeemeeting in committeemeetings:
        featured.committee_meeting_report.append(committeemeeting)
    for tabledreport in tabledreports:
        featured.tabled_committee_report.append(tabledreport)
    featured.title = "LivemagSA Launched Live From Parliament"
    featured.blurb = "For the next six months, LiveMagSA be teaming up with PMG to report directly from parliament, bringing you the highlights and telling you about the policy decisions that affect you."
    featured.link = "http://livemag.co.za/welcome-parliament/"
    db.session.add(featured)
    db.session.commit()

def clear_db():
    logger.debug("Dropping all")
    db.drop_all()
    logger.debug("Creating all")
    db.create_all()

def disable_reindexing():
    Search.reindex_changes = False


def merge_billtracker():

    with open ("data/billtracker_dump.txt", "r") as f:
        data=f.read()
        bills = json.loads(data)
        for rec in bills:
            bill_obj = Bill(
                title=rec['name'],
                number=rec['number'],
                year=rec['year'],
                )
            if rec.get('bill_type'):
                bill_obj.type = BillType.query.filter_by(name=rec['bill_type']).one()
            if rec.get('status'):
                bill_obj.status = BillStatus.query.filter_by(name=rec['status']).one()
            # date_of_introduction
            # date_of_assent
            # effective_date
            # act_name
            # place_of_introduction_id
            # place_of_introduction
            # introduced_by_id
            # introduced_by
            db.session.add(bill_obj)
            db.session.commit()
    return


if __name__ == '__main__':
    disable_reindexing()
    clear_db()
    rebuild_db()
    rebuild_table("hansard", Hansard, { "title": "title", "meeting_date": "meeting_date", "start_date": "start_date", "body": "body" })
    rebuild_table("briefing", Briefing, {"title": "title", "briefing_date": "briefing_date", "summary": "summary", "minutes": "minutes", "presentation": "presentation", "start_date": "start_date" })
    rebuild_table("questions_replies", QuestionReply, {"title": "title", "body": "body", "start_date": "start_date", "question_number": "question_number"})
    rebuild_table("tabled_committee_report", TabledCommitteeReport, { "title": "title", "start_date": "start_date", "body": "body", "summary": "teaser", "nid": "nid" })
    rebuild_table("calls_for_comment", CallForComment, { "title": "title", "start_date": "start_date", "end_date": "comment_exp", "body": "body", "summary": "teaser", "nid": "nid" })
    rebuild_table("policy_document", PolicyDocument, { "title": "title", "effective_date": "effective_date", "start_date": "start_date", "nid": "nid" })
    rebuild_table("gazette", Gazette, { "title": "title", "effective_date": "effective_date", "start_date": "start_date", "nid": "nid" })
    rebuild_table("book", Book, { "title": "title", "summary": "teaser", "start_date": "start_date", "body": "body", "nid": "nid" })
    rebuild_table("daily_schedule", DailySchedule, { "title": "title", "start_date": "start_date", "body": "body", "schedule_date": "daily_sched_date", "nid": "nid" })
    # bills()
    add_featured()

    # add default roles
    admin_role = Role(name="editor")
    db.session.add(admin_role)
    superuser_role = Role(name="user-admin")
    db.session.add(superuser_role)
    # add a default admin user
    user = User(email="admin@pmg.org.za", password="3o4ukjren3", active=True, confirmed_at=datetime.datetime.now())
    user.roles.append(admin_role)
    user.roles.append(superuser_role)
    db.session.add(user)
    db.session.commit()

    # add billtracker data
    merge_billtracker()
