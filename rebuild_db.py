import os
import json
import time, datetime
from backend.app import app, db, logger
from backend.models import *
import parsers

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


def rebuild_db():
    """
    Save json fixtures into a structured database, intended for use in our app.
    """
    
    db.drop_all()
    db.create_all()

    start = time.time()

    # populate houses of parliament
    joint_obj = Organisation(name="Joint (NA + NCOP)", type="house", version=0)
    ncop_obj = Organisation(name="NCOP", type="house", version=0)
    na_obj = Organisation(name="National Assembly", type="house", version=0)
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
            organisation.parent_id = ncop_obj.id
        elif "joint" in organisation.name.lower():
            organisation.parent_id = joint_obj.id
        else:
            organisation.parent_id = na_obj.id

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
            party_obj = Organisation.query.filter_by(type="party").filter_by(name=party).first()
            if not party_obj:
                party_obj = Organisation(type="party", name=party, version=0)
                db.session.add(party_obj)
                db.session.commit()
            membership_obj = Membership(organisation=party_obj)
            member_obj.memberships.append(membership_obj)

        # set house membership
        house = member['mp_province']
        if house == "National Assembly":
            member_obj.memberships.append(Membership(organisation=na_obj))
        elif house and "NCOP" in house:
            member_obj.memberships.append(Membership(organisation=ncop_obj))
            logger.debug(house)
            province_obj = Organisation.query.filter_by(type="province").filter_by(name=house[5::]).first()
            if not province_obj:
                province_obj = Organisation(type="province", name=house[5::], version=0)
                db.session.add(province_obj)
                db.session.commit()
            member_obj.memberships.append(Membership(organisation=province_obj))

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
            if i % 1000 == 0:
                logger.debug("writing 1000 reports...")
                db.session.commit()

    # ======= BILLS ======== #
    bills = read_data("bill.json")
    logger.debug("Processing Bills")
    for billobj in bills:
        bill = Bill()
        if (len(billobj["revisions"]) > 0):
            # print billobj
            bill.name = billobj["revisions"][0]["title"]
        else:
            bill.name = billobj["title"]
        if (billobj["effective_date"]):
            bill.effective_date = datetime.datetime.fromtimestamp(float(billobj["effective_date"]))
        if (billobj["files"]):
            for f in billobj["files"]:
                docobj = BillFile(
                    filemime=f["filemime"],
                    origname = f["origname"],
                    # description = f["field_file_bill_data"]["description"],
                    url = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/" + f["filename"],
                )
                if ("version" in f):
                    bill.code = f["version"]
                # if ("field_file_bill_data" in f):
                #     print docobj
                #     print f["field_file_bill_data"]
                #     field_file_bill_data = f["field_file_bill_data"]
                    # if ((f["field_file_bill_data"]) and ("description" in  f["field_file_bill_data"])):
                    #     docobj.description = f["field_file_bill_data"]["description"]
                # print docobj
                bill.files.append(docobj)
        db.session.add(bill)
    bills = ""

    # ======= HANSARDS ======== #
    hansards = read_data("hansard.json")
    logger.debug("Processing Hansards")
    for hansardobj in hansards:
        newobj = construct_obj(hansardobj, { "title": "title", "meeting_date": "meeting_date", "body": "body" })
        if (newobj["meeting_date"]):
            newobj["meeting_date"] = db_date_from_utime(newobj["meeting_date"])
        hansard = Hansard()
        for key,val in newobj.iteritems():
            setattr(hansard,key, val)
        db.session.add(hansard)
    db.session.commit()
    return


if __name__ == '__main__':

    rebuild_db()