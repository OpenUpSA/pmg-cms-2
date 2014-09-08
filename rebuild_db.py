import os
import json
import time
from backend.app import app, db, logger
from backend.models import *
import parsers

STATIC_HOST = app.config['STATIC_HOST']


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


def rebuild_db(db_name):
    """
    Save json fixtures into a structured database, intended for use in our app.
    """

    dump_db(db_name)
    db.create_all()

    start = time.time()

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
                logger.debug("MULTIPLE REVISIONS")
    for key, val in committees.iteritems():
        logger.debug(key)
        organisation = Organisation()
        organisation.name = key
        organisation.type = "committee"
        organisation.version = 0

        commitee_info = CommitteeInfo()
        if val.get("about"):
            commitee_info.about = val["about"]
        if val.get("contact"):
            commitee_info.contact_details = val["contact"]
        commitee_info.organization = organisation

        db.session.add(organisation)
        db.session.add(commitee_info)
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
                member_obj.memberships.append(org_model)
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
            member_obj.memberships.append(party_obj)

        # set house membership
        house = member['mp_province']
        if house:
            logger.debug(house)
            house_obj = Organisation.query.filter_by(type="house").filter_by(name=house).first()
            if not house_obj:
                house_obj = Organisation(type="house", name=house, version=0)
                db.session.add(house_obj)
            member_obj.memberships.append(house_obj)

        db.session.add(member_obj)
        logger.debug('')
    db.session.commit()

    # populate committee reports
    reports = read_data('report.json')
    i = 0
    meeting_event_type_obj = EventType(name="committee-meeting")
    db.session.add(meeting_event_type_obj)
    db.session.commit()
    for report in reports:
        parsed_report = parsers.MeetingReportParser(report)

        report_obj = Content(
            type="committee-meeting-report",
            title=parsed_report.title,
            body=parsed_report.body,
            version=0
        )
        db.session.add(report_obj)

        committee_obj = Organisation.query.filter_by(type="committee").filter_by(name=parsed_report.committee).first()
        event_obj = Event(
            event_type=meeting_event_type_obj,
            organisation=committee_obj,
            date=parsed_report.date,
            content=report_obj
        )
        db.session.add(event_obj)
        i += 1
        if i % 1000 == 0:
            db.session.commit()
    db.session.commit()
    return


if __name__ == '__main__':

    rebuild_db('instance/tmp.db')