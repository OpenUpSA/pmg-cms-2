import requests
from logging import getLogger
import uuid

from pmg import app


log = getLogger(__name__)


class Sharpspring(object):
    url = 'http://api.sharpspring.com/pubapi/v1/'

    def __init__(self):
        self.api_key = app.config['SHARPSPRING_API_KEY']
        self.api_secret = app.config['SHARPSPRING_API_SECRET']

    def subscribeToList(self, user, listId):
        # ensure sharpspring has the email
        details = {
            'emailAddress': user.email,
        }
        if user.organisation:
            details['companyName'] = user.organisation.name

        resp = self.call('createLeads', {'objects': [details]})
        # 301 means already exists
        if not resp['error'] and resp['result'] and (resp['result']['creates'][0]['success'] or resp['result']['creates'][0]['error']['code'] == 301):
            # all good
            log.info("Lead created.")
        else:
            log.erro("Couldn't create SharpSpring contact: %s" % resp)
            raise ValueError("Couldn't subscribe to SharpSpring: %s" % resp)

        # subscribe to list
        resp = self.call('addListMemberEmailAddress', {
            'emailAddress': user.email,
            'listID': listId,
        })
        # 213 means already subscribed. Note that the response format for this call and the
        # above one differ
        if not resp['error'] or resp['error']['code'] == 213 or (resp['result'] and resp['result']['creates'][0]['success']):
            # all good
            log.info("Subscribed.")
        else:
            log.error("Couldn't subscribe to SharpSpring: %s" % resp)
            raise ValueError("Couldn't subscribe to SharpSpring: %s" % resp)

    def call(self, method, params):
        body = {
            'id': uuid.uuid4().get_hex(),
            'method': method,
            'params': params,
        }
        log.info("Calling SharpSpring: %s" % body)

        resp = requests.post(
            self.url,
            params={
                'accountID': self.api_key,
                'secretKey': self.api_secret,
            }, json=body)
        resp.raise_for_status()

        data = resp.json()
        log.debug("Response: %s" % data)
        return data
