import sys
import math
import argparse
import logging

import requests
from pyelasticsearch import ElasticSearch
from sqlalchemy import types
from inflection import underscore, camelize

from app import db, app
import models
from transforms import *

class Search:

    esserver = app.config['ES_SERVER']
    index_name = "pmg"
    search_fields = ["title^3", "description^2", "fulltext"]
    es = ElasticSearch(esserver)
    per_batch = 50
    logger = logging.getLogger(__name__)

    def reindex_all(self, data_type):
        """ Index all content of a data_type """
        try:
            self.drop_index(data_type)
        except:
            self.logger.warn("Couldn't find %s index" % data_type)

        Model = self.model_for_data_type(data_type)
        ids = [r[0] for r in db.session.query(Model.id).all()]

        count = len(ids)
        pages = int(math.ceil(float(count) / float(self.per_batch)))
        self.logger.info("Pages %s, Count %s" % (pages, count))

        while len(ids):
            self.logger.info("Items left %s" % len(ids))
            id_subsection = []
            for x in xrange(0, self.per_batch):
                if ids:
                    id_subsection.append(ids.pop())

            rows = db.session.query(Model).filter(Model.id.in_(id_subsection)).all()
            items = [Transforms.serialise(data_type, r) for r in rows]
            self.add_many(data_type, items)

    def drop_index(self, data_type):
        self.logger.info("Dropping %s index" % data_type)
        self.es.delete_all(self.index_name, data_type)
        self.logger.info("Dropped %s index" % data_type)

    def add_obj(self, obj):
        data_type = self.data_type_for_obj(obj)
        item = Transforms.serialise(data_type, obj)
        self.add(data_type, item)

    def add_many(self, data_type, items):
        self.es.bulk_index(self.index_name, data_type, items)

    def add(self, data_type, item):
        self.add_many(data_type, [item])

    def delete_obj(self, obj):
        self.delete(self.data_type_for_obj(obj), obj.id)

    def data_type_for_obj(self, obj):
        # QuestionReply -> question_reply
        return underscore(type(obj).__name__)

    def model_for_data_type(self, data_type):
        # question_reply -> QuestionReply class
        return getattr(models, camelize(data_type))

    def delete(self, data_type, uid):
        try:
            self.es.delete(self.index_name, data_type, uid)
        except ElasticHttpNotFoundError:
            pass

    def get(self, data_type, uid):
        try:
            return self.es.get(self.index_name, data_type, uid)
        except:
            return False

    def indexable(self, obj):
        """ Should this object be indexed for searching? """
        return self.data_type_for_obj(obj) in Transforms.convert_rules

    def mapping(self, data_type):
        mapping = {
            "properties": {
                "title": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                },
                "fulltext": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                },
                "description": {
                    "type": "string",
                    "analyzer": "english",
                    "index_options": "offsets"
                }
            }
        }
        self.es.put_mapping(self.index_name, data_type, mapping)

    def search(
            self,
            query,
            size=10,
            es_from=0,
            start_date=False,
            end_date=False,
            content_type=False,
            committee=False):
        q = {
            "from": es_from,
            "size": size,
            "query": {
                "filtered": {
                    "filter": {},
                    "query": {},
                },
            },
        }
        q["query"]["filtered"]["query"] = {
            "multi_match": {
                "query": query,
                "fields": self.search_fields,
                "type": "phrase"
            },
        }
        if start_date and end_date:
            q["query"]["filtered"]["filter"]["range"] = {
                "date": {
                    "gte": start_date,
                    "lte": end_date,
                }
            }
        if committee:
            q["query"]["filtered"]["filter"]["term"] = {
                "committee_id": committee
            }

        q["highlight"] = {
            "pre_tags": ["<strong>"],
            "post_tags": ["</strong>"],
            "fields": {
                "title": {},
                "description": {
                    "fragment_size": 500,
                    "number_of_fragments": 1,
                    "no_match_size": 250,
                    "tag_schema": "styled"},
                "fulltext": {
                    "fragment_size": 500,
                    "number_of_fragments": 1,
                    "no_match_size": 250,
                    "tag_schema": "styled"}}}
        self.logger.debug("query_statement: %s" % q)
        if (content_type):
            return self.es.search(
                q,
                index=self.index_name,
                doc_type=content_type)
        else:
            return self.es.search(q, index=self.index_name)

    def count(
            self,
            query,
            content_type=False,
            start_date=False,
            end_date=False):
        q1 = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": self.search_fields,
                    "type": "phrase"
                },
            },
            "aggregations": {
                "types": {
                    "terms": {
                        "field": "_type"
                    }
                }
            }
        }
        q2 = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": self.search_fields,
                    "type": "phrase"
                },
            },
            "aggregations": {
                "years": {
                    "date_histogram": {
                        "field": "date",
                        "interval": "year"
                    }
                }
            }
        }
        return [
            self.es.search(
                q1,
                index=self.index_name,
                size=0),
            self.es.search(
                q2,
                index=self.index_name,
                size=0)]

    def reindex_everything(self):
        for data_type in Transforms.data_types():
            self.reindex_all(data_type)


if __name__ == "__main__":
    # print "ElasticSearch PMG library"
    parser = argparse.ArgumentParser(description='ElasticSearch PMG library')
    parser.add_argument(
        '--import',
        dest='import_data_type',
        choices=Transforms.data_types(),
        help='Imports the data from a content type to ElasticSearch')
    parser.add_argument('--test', action="store_true")
    parser.add_argument('--reindex', action="store_true")
    args = parser.parse_args()

    # limit logging
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    search = Search()
    if (args.test):
        search.test()
    if (args.import_data_type):
        search.reindex_all(args.import_data_type)
    if (args.reindex):
        search.reindex_everything()
