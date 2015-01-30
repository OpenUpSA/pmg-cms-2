import json
from backend.app import app, db
from backend.models import *
from dateutil import tz
from datetime import datetime
from sqlalchemy.exc import IntegrityError

db.echo = False

alert_subscriptions = {}
access_subscriptions = {}
committee_map = {}

domain_map = {}
organisations_list = Organisation.query.all()
for organisation in organisations_list:
    domain_map[organisation.domain] = organisation

# read in json user dump
with open('data/users_new.json', 'r') as f:

    for line in f.readlines():
        user_rec = json.loads(line)
        # create user if it doesn't exist yet, to account for new users since we fist migrated the db
        user = User.query.filter(User.email==user_rec['mail']).first()
        if user is None:
            user = User()
            user.name = user_rec.get('name')
            user.email = user_rec.get('mail')
            user.active = True if user_rec.get('status') == "1" else False
            user.last_login_at = datetime.fromtimestamp(int(user_rec.get('login')), tz=tz.gettz('UTC'))
            user.password = user_rec.get('pass')
            # link user to organisation
            user_domain = user_rec['mail'].split("@")[-1]
            if domain_map.get(user_domain):
                user.organisation = domain_map.get(user_domain)
            db.session.add(user)
            print "adding new user: " + user.email
            db.session.commit()
        # extract user access subscriptions
        access_subscriptions[user] = user_rec['alerts']
        for committee in user_rec['alerts']:
            if not committee_map.get(committee['name']):
                committee_map[committee['name']] = Committee.query.filter(Committee.name==committee['name'].strip().encode('utf8')).first()
        # extract user alert subscriptions
        alert_subscriptions[user] = user_rec['subscribed']
        for committee in user_rec['subscribed']:
            if not committee_map.get(committee['name']):
                committee_map[committee['name']] = Committee.query.filter(Committee.name==committee['name'].strip().encode('utf8')).first()

for committee_name_str, committee_obj in committee_map.iteritems():

    if committee_obj is None:
        print committee_name_str.encode('utf8')

# Subscribe to alerts
print "\n---------------------------------------"
print 'Setting alert subscriptions'
i = 0
for user, subscription_list in alert_subscriptions.iteritems():
    i += 1
    new_committee_alerts = []
    for committee in subscription_list:
        try:
            if committee_map.get(committee['name']):
                new_committee_alerts.append(committee_map[committee['name']])
        except Exception:
            print committee
            raise
    user.committee_alerts = new_committee_alerts
    db.session.add(user)
    if i % 20 == 0:
        print "committing 20 users to db (" + str(i) + " done so far)"
        db.session.commit()

db.session.commit()

# Set access to premium content
print "\n---------------------------------------"
print 'Setting user access to premium content'
i = 0
for user, subscription_list in access_subscriptions.iteritems():
    i += 1
    new_access_subscriptions = []
    for committee in subscription_list:
        try:
            if committee_map.get(committee['name']):
                new_access_subscriptions.append(committee_map[committee['name']])
        except Exception:
            print committee
            raise
    user.subscriptions = new_access_subscriptions
    db.session.add(user)
    if i % 20 == 0:
        print "committing 20 users to db (" + str(i) + " done so far)"
        db.session.commit()

db.session.commit()
