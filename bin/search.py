#!/bin/env python

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
from pmg.search import Search, Transforms

if __name__ == "__main__":
    data_types = Transforms.data_types() + ['all']

    parser = argparse.ArgumentParser(description='ElasticSearch PMG library')
    parser.add_argument('data_type', metavar='DATA_TYPE', choices=data_types, help='Data type to manipulate: %s' % data_types)
    parser.add_argument('--reindex', action="store_true")
    parser.add_argument('--delete', action="store_true")
    args = parser.parse_args()

    search = Search()

    if args.reindex:
        if args.data_type == 'all':
            search.reindex_everything()
        else:
            search.reindex_all(args.data_type)

    if args.delete:
        search.delete_everything()
