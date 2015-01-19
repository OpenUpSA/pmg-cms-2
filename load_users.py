import json
from backend.app import app, db
from backend.models import *
from dateutil import tz
from datetime import datetime
from sqlalchemy.exc import IntegrityError

db.echo = False

with open('data/users.json', 'r') as f:
    user_list = []
    for line in f.readlines():
        user_list.append(json.loads(line))


with open('data/user_organisation.json', 'r') as f:
    org_list = []
    for line in f.readlines():
        org_list.append(json.loads(line))


if __name__ == '__main__':

    # print len(user_list), "users"
    # print json.dumps(user_list[5], indent=4)
    # print json.dumps(user_list[500], indent=4)
    # print json.dumps(user_list[-1], indent=4)
    #
    # print len(org_list), "organisations"
    # print json.dumps(org_list[5], indent=4)
    # print json.dumps(org_list[50], indent=4)
    # print json.dumps(org_list[-1], indent=4)

    committee_map = {}
    committee_list = Committee.query.all()
    for committee in committee_list:
        committee_map[committee.name.encode('utf8')] = committee

    print len(committee_map.keys()), " committees available"
    print json.dumps(committee_map.keys(), indent=4)

    # # load organisations into db
    # domain_map = {}
    # i = 0
    # for org in org_list:
    #     i += 1
    #     # populate org model
    #     print i, org.get('domain')
    #     org_obj = Organisation.query.filter_by(domain=org.get('domain')).first()
    #     if org_obj is None:
    #         # raise Exception("Could not find org")
    #         org_obj = Organisation()
    #     org_obj.name = org.get('name')
    #     org_obj.domain = org.get('domain')
    #     org_obj.paid_subscriber = True if org.get('paid_sub') == "1" else False
    #     org_obj.created_at = datetime.fromtimestamp(int(org.get('created')), tz=tz.gettz('UTC'))
    #     org_obj.expiry = datetime.fromtimestamp(int(org.get('expiry')), tz=tz.gettz('UTC'))
    #
    #     # set committee access subscriptions
    #     if not org_obj.subscriptions and org.get('terms'):
    #         for item in org['terms']:
    #             committee = committee_map.get(item.get('name'))
    #             if committee is None:
    #                 print "NOT FOUND: ", item.get('name')
    #                 raise Exception("Could not find committee")
    #             org_obj.subscriptions.append(committee)
    #         print len(org_obj.subscriptions), "subscriptions"
    #
    #     db.session.add(org_obj)
    #     domain_map[org['domain']] = org_obj
    #     if i % 20 == 0:
    #         db.session.commit()
    #
    # db.session.commit()

    domain_map = {}
    organisations_list = Organisation.query.all()
    for organisation in organisations_list:
        domain_map[organisation.domain] = organisation

    missing_committee = Committee.query.filter_by(name="Ad Hoc Committee - President's Submission in response to Public Protector's Report").one()
    map = {
        "Ad Hoc Committee - President\u2019s Submission in response to Public Protector\u2019s Report": missing_committee,
    }


    not_found = []
    # load users
    i = 0
    for user in user_list:
        i += 1
        # populate user model
        user_obj = User.query.filter_by(email=user.get('mail')).first()

        if user.get('mail'):
            # print user.get('mail'), "[" + user.get('name') + "]"
            if user_obj is None:
                user_obj = User()
                user_obj.name = user.get('name')
                user_obj.email = user.get('mail')
                user_obj.active = True if user.get('status') == "1" else False
                user_obj.last_login_at = datetime.fromtimestamp(int(user.get('login')), tz=tz.gettz('UTC'))
                user_obj.password = user.get('pass')

            # link user to organisation
            user_domain = user['mail'].split("@")[-1]
            if domain_map.get(user_domain):
                user_obj.organisation = domain_map.get(user_domain)

            # set notification subscriptions
            if user.get('subscribed'):
                for item in user['subscribed']:
                    committee_name = item.get('name').strip().encode('utf8')
                    committee = committee_map.get(committee_name)
                    if committee is None:
                        if map.get(committee_name):
                            committee = map[committee_name]
                        elif not committee_name in not_found:
                            not_found.append(committee_name)
                    if committee and not committee in user_obj.subscriptions:
                        user_obj.subscriptions.append(committee)

            db.session.add(user_obj)
        if i % 50 == 0:
            db.session.commit()

    db.session.commit()

    print len(not_found), " committees not found"
    print json.dumps(not_found, indent=4)
