import json
from backend.app import app, db
from backend.models import *
from dateutil import tz
from datetime import datetime

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
        committee_map[committee.name] = committee

    print json.dumps(committee_map.keys(), indent=4)

    # load organisations into db
    domain_map = {}
    for org in org_list:
        # populate org model
        # print org.get('domain')
        org_obj = Organisation.query.filter_by(domain=org.get('domain')).first()
        if org_obj is None:
            org_obj = Organisation()
        org_obj.name = org.get('name')
        org_obj.domain = org.get('domain')
        org_obj.paid_subscriber = True if org.get('paid_sub') == 1 else False
        org_obj.created_at = datetime.fromtimestamp(int(org.get('created')), tz=tz.gettz('UTC'))
        org_obj.expiry = datetime.fromtimestamp(int(org.get('expiry')), tz=tz.gettz('UTC'))

        # set committee access subscriptions
        if org.get('terms'):
            for item in org['terms']:
                committee = committee_map.get(item.get('name'))
                if committee is None:
                    print "NOT FOUND: ", item.get('name')
                org_obj.subscriptions.append(committee)

        db.session.add(org_obj)
        domain_map[org['domain']] = org_obj

    print json.dumps(committee_map.keys(), indent=4)

    # db.session.commit()

    # load users
    for user in user_list:
        # populate user model
        # print user.get('mail'), "[" + user.get('name') + "]"
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
                committee = committee_map.get(item.get('name').strip(" "))
                if committee is None:
                    print "NOT FOUND: ", item.get('name')
                user_obj.subscriptions.append(committee)

        db.session.add(user_obj)

    # db.session.commit()
