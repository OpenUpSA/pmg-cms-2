"""
Once-off script to be run before the migration to introduce an uniqueness 
constraint on commitee_id and organisation_id in the committee_organsation 
table is run. This script will delete all duplicate committee_organisation
entries and insert one new record instead.
"""
#!/bin/env python

import argparse
import os
import sys
import csv

from sqlalchemy import func

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.abspath(os.path.join(file_path, os.pardir)))

from pmg.models.resources import Committee, House
from pmg import db
from pmg.models.users import organisation_committee


def remove_duplicate_subscriptions(commit=False):
    subscription_groups = (
        db.session.query(
            organisation_committee,
            func.count(organisation_committee.c.organisation_id).label("count"),
        )
        .group_by(organisation_committee.c.committee_id)
        .group_by(organisation_committee.c.organisation_id)
        .all()
    )
    for subscription_group in subscription_groups:
        # If there's only a single record, we don't need to delete anything
        if subscription_group.count == 1:
            continue
        # Delete all of the duplicate subscriptions
        # We need to delete all of them because the table doesn't have a primary key
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
        # Create single new record to replace the deleted duplicate records
        print(
            f"Inserting: Committee: {subscription_group.committee_id}, Organisation: {subscription_group.organisation_id}"
        )
        insert = organisation_committee.insert().values(
            committee_id=subscription_group.committee_id,
            organisation_id=subscription_group.organisation_id,
        )
        db.session.execute(insert)

    if commit:
        print("Committing changes to database.")
        db.session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete duplicate subscriptions (committee_organsation)"
    )
    parser.add_argument(
        "--commit",
        help="Commit deletions to database",
        default=False,
        action="store_true",
    )
    args = parser.parse_args()

    remove_duplicate_subscriptions(commit=args.commit)
