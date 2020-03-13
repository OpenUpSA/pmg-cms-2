#!/bin/env python

import argparse
import os
import sys
import csv

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Committee, House
from pmg import db
from pmg.models.users import organisation_committee


def get_subscriptions():
    subscription_groups = (
        db.session.query(organisation_committee)
        .group_by(organisation_committee.c.committee_id)
        .group_by(organisation_committee.c.organisation_id)
        .all()
    )
    for subscription_group in subscription_groups:
        # Delete all
        print(
            f"Deleting: Committee: {subscription_group.committee_id}, Organisation: {subscription_group.organisation_id}"
        )
        subscriptions = (
            db.session.query(organisation_committee)
            .filter(
                organisation_committee.c.committee_id == subscription_group.committee_id
            )
            .filter(
                organisation_committee.c.organisation_id
                == subscription_group.organisation_id
            )
            .delete(synchronize_session=False)
        )
        # Create new
        print(
            f"Inserting: Committee: {subscription_group.committee_id}, Organisation: {subscription_group.organisation_id}"
        )
        insert = organisation_committee.insert().values(
            committee_id=subscription_group.committee_id,
            organisation_id=subscription_group.organisation_id,
        )
        db.session.execute(insert)
    db.session.commit()


if __name__ == "__main__":
    get_subscriptions()
