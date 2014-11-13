import os
import json
import time, datetime
from backend.app import app, db

from backend import models
from backend.models import *
import parsers
from sqlalchemy import types

import requests

import logging
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').level = logging.WARN

STATIC_HOST = app.config['STATIC_HOST']
db.echo = False

def strip_filpath(filepath):

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
    return datetime.datetime.fromtimestamp(float(utime))

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
                    url = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/" + f["filename"],
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
                    url = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/audio/" + f["filename"],
                    playtime = f["playtime"],
                    description = f["title_format"]
                )
            db.session.add(fobj)
            files.append(fobj)
        db.session.commit()
    return files

def prep_table(tablename):
    Model = getattr(models, tablename.capitalize())
    print "Deleted rows: ", Model.query.delete()
    

def rebuild_table(tablename, mappings):
    logger.debug("Rebuilding %s" % tablename)
    Model = getattr(models, tablename.capitalize())
    prep_table(tablename)
    i = 0
    with open('data/' + tablename + '.json', 'r') as f:
        records = []
        lines = f.readlines()
        logger.debug("Found %i records" % (len(lines)))
        for line in lines:
            obj = json.loads(line)
            newobj = construct_obj(obj, mappings)
            # Check for Dates
            for mapping in mappings.values():
                row_type = getattr(Model, mapping).property.columns[0].type
                if (row_type.__str__() == "DATE"):
                    if (newobj[mapping]):
                        newobj[mapping] = db_date_from_utime(newobj[mapping])
            model = Model()
            files = find_files(obj)
            if (len(files)):
                for f in files:
                    model.files.append(f)
            for key,val in newobj.iteritems():
                setattr(model, key, val)
            db.session.add(model)
            i += 1
            if (i == 100):
                db.session.commit()
                i = 0
                logger.debug("Wrote 100 rows...")        
        db.session.commit()

def rebuild_db():
    """
    Save json fixtures into a structured database, intended for use in our app.
    """

    db.drop_all()
    db.create_all()

    start = time.time()

    # populate houses of parliament
    joint_obj = House(name="Joint (NA + NCOP)")
    ncop_obj = House(name="NCOP")
    na_obj = House(name="National Assembly")
    for obj in [joint_obj, ncop_obj, na_obj]:
        db.session.add(obj)
    db.session.commit()

    # populate membership_type
    chairperson = MembershipType(name="chairperson")
    db.session.add(chairperson)
    db.session.commit()

    # populate committees
    committees = {}
    drupal_recs = read_data('comm_info_page.json')
    for rec in drupal_recs:
        if rec['terms']:
            name = rec['terms'][0].strip()
            if not committees.get('name'):
                committees[name] = {}
            if rec['comm_info_type'] == '"Contact"':
                committees[name]["contact"] = rec["revisions"][0]["body"]
            elif rec['comm_info_type'] == '"About"':
                committees[name]["about"] = rec["revisions"][0]["body"]
            if len(rec["revisions"]) > 1:
                logger.debug("ERROR: MULTIPLE REVISIONS PRESENT FOR A COMMITTEE")
    for key, val in committees.iteritems():
        logger.debug(key)
        organisation = Organisation()
        organisation.name = key
        organisation.type = "committee"
        organisation.version = 0

        # set parent relation
        if "ncop" in organisation.name.lower():
            organisation.house_id = ncop_obj.id
        elif "joint" in organisation.name.lower():
            organisation.house_id = joint_obj.id
        else:
            organisation.house_id = na_obj.id

        committee_info = CommitteeInfo()
        if val.get("about"):
            committee_info.about = val["about"]
        if val.get("contact"):
            committee_info.contact_details = val["contact"]
        committee_info.organization = organisation

        db.session.add(organisation)
        db.session.add(committee_info)
        val['model'] = organisation
    db.session.commit()

    # populate committee members
    members = read_data('committee_member.json')
    for member in members:
        member_obj = Member(
            name=member['title'].strip(),
            version=0
        )
        if member.get('files'):
            # logger.debug(json.dumps(member['files'], indent=4)
            member_obj.profile_pic_url = STATIC_HOST + strip_filpath(member["files"][-1]['filepath'])
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
                membership_obj = Membership(organisation=org_model)
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
    tmp_committees = Organisation.query.filter_by(type="committee").all()
    for committee in tmp_committees:
        if committee.memberships:
            membership_obj = committee.memberships[0]
            membership_obj.type_id = 1
            db.session.add(membership_obj)
    db.session.commit()

    # populate committee reports
    # reports = read_data('report.json')

    i = 0
    meeting_event_type_obj = EventType(name="committee-meeting")
    db.session.add(meeting_event_type_obj)
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
                type=meeting_event_type_obj,
                organisation=committee_obj,
                date=parsed_report.date,
                title=parsed_report.title
            )
            db.session.add(event_obj)

            report_obj = Content(
                type="committee-meeting-report",
                body=parsed_report.body,
                summary=parsed_report.summary,
                event=event_obj,
                version=0
            )
            db.session.add(report_obj)

            for item in parsed_report.related_docs:
                doc_obj = Content(
                    event=event_obj,
                    type=item["filemime"],
                    version=0
                )
                doc_obj.file_path=item["filepath"]
                doc_obj.title=item["title"]
                db.session.add(doc_obj)

            for item in parsed_report.audio:
                audio_obj = Content(
                    event=event_obj,
                    type=item["filemime"],
                    version=0
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
        bill.bill_type_id = addChild(BillType, billobj["bill_type"])
        # place_of_introduction_id = db.Column(db.Integer, db.ForeignKey('organisation.id'))
        # place_of_introduction = db.relationship('Organisation')
        # introduced_by_id = db.Column(db.Integer, db.ForeignKey('member.id'))
        # introduced_by = db.relationship('Member')
        db.session.add(bill)
    db.session.commit()

def clear_db():
    logger.debug("Dropping all")
    db.drop_all()
    logger.debug("Creating all")
    db.create_all()


if __name__ == '__main__':
    clear_db()
    
    # rebuild_table("policy_document", { "title": "title", "effective_date": "effective_date" })
    rebuild_db()
    rebuild_table("hansard", { "title": "title", "meeting_date": "meeting_date", "body": "body" })
    bills()
    rebuild_table("briefing", {"title": "title", "briefing_date": "briefing_date", "summary": "summary", "minutes": "minutes", "presentation": "presentation"})
    rebuild_table("questions_replies", {"title": "title", "body": "body", "start_date": "start_date", "question_number": "question_number"})
