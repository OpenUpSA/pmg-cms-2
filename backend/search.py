import sys
import math
import argparse
import logging
import json

import requests
from pyelasticsearch import ElasticSearch
from pyelasticsearch.exceptions import ElasticHttpNotFoundError

from sqlalchemy import types
from inflection import camelize
from bs4 import BeautifulSoup

from frontend import db, app
import models

class Search:

    esserver = app.config['ES_SERVER']
    index_name = "pmg"
    search_fields = ["title^2", "description", "fulltext"]
    search_type = "cross_fields"
    es = ElasticSearch(esserver)
    per_batch = 50
    logger = logging.getLogger(__name__)

    reindex_changes = app.config['SEARCH_REINDEX_CHANGES']
    """ Should updates to models be reindexed? """


    def reindex_all(self, data_type):
        """ Index all content of a data_type """
        try:
            self.drop_index(data_type)
            self.mapping(data_type)
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
        return getattr(obj, 'resource_content_type', None)

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
        dt = self.data_type_for_obj(obj)
        return self.reindex_changes and dt and dt in Transforms.convert_rules

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
                },
                "number": {
                    "type": "integer",
                },
                "year": {
                    "type": "integer",
                },
            }
        }
        self.es.put_mapping(self.index_name, data_type, mapping)

    def build_filters(self, start_date, end_date, document_type, committee):
        filters = {}

        if start_date and end_date:
            filters["date"] = {
                "range": {
                    "date": {
                        "gte": start_date,
                        "lte": end_date,
                    }
                }
            }

        if committee:
            filters["committe"] = {
                "term": {"committee_id": committee}
            }

        if document_type:
            filters["document_type"] = {
                "term": {"_type": document_type},
            }

        return filters


    def search(self, query, size=10, es_from=0, start_date=False, end_date=False, document_type=False, committee=False):
        filters = self.build_filters(start_date, end_date, document_type, committee)

        q = {
            # We do two queries, one is a general term query across the fields,
            # the other is a phrase query. At the very least, items *must*
            # match the term search, and items are preferred if they
            # also match the phrase search.
            "bool": {
                "must": {
                    # best across all the fields
                    "multi_match": {
                        "query": query,
                        "fields": self.search_fields,
                        "type": "best_fields",
                        # this helps skip stopwords, see
                        # http://www.elasticsearch.org/blog/stop-stopping-stop-words-a-look-at-common-terms-query/
                        "cutoff_frequency": 0.0007,
                        "operator": "and",
                    },
                },
                "should": {
                    # try to match to a phrase
                    "multi_match": {
                        "query": query,
                        "fields": self.search_fields,
                        "type": "phrase"
                    },
                }
            }
        }

        aggs = {
            "types": {
                "filter": {"and": {"filters": [v for k, v in filters.iteritems() if k != "document_type"]}},
                "aggs": {"types": {
                    "terms": {"field": "_type"}
                }},
            },
            "years": {
                "filter": {"and": {"filters": [v for k, v in filters.iteritems() if k != "date"]}},
                "aggs": {"years": {
                    "date_histogram": {
                        "field": "date",
                        "interval": "year"
                    },
                }},
            }
        }

        q = {
            "from": es_from,
            "size": size,
            "sort": {'_score': {'order': 'desc'}},
            # don't return big fields
            "_source": {"exclude": ["fulltext", "description"]},
            "query": q,
            # filter the results after the query, so that the per-aggregation filters
            # aren't impacted by these filters. See
            # http://www.elasticsearch.org/guide/en/elasticsearch/guide/current/_post_filter.html
            "post_filter": {"and": {"filters": filters.values()}},
            "aggs": aggs,
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "order" : "score",
                "fragment_size": 80,
                "no_match_size": 0,
                "fields": {
                    "title": {
                        "number_of_fragments": 0,
                    },
                    "description": {
                        "number_of_fragments": 2,
                    },
                    "fulltext": {
                        "number_of_fragments": 2,
                    }
                }
            }
        }

        self.logger.debug("query_statement: %s" % json.dumps(q, indent=2))
        return self.es.search(q, index=self.index_name)

    def reindex_everything(self):
        data_types = Transforms.data_types()

        self.logger.info("Reindexing everything: %s" % data_types)
        self.delete_everything()
        self.create_index()

        for data_type in data_types:
            self.reindex_all(data_type)

    def delete_everything(self):
        self.es.delete_index(self.index_name)        

    def create_index(self):
        self.es.create_index(self.index_name)


class Transforms:
    @classmethod
    def data_types(cls):
        return cls.convert_rules.keys()

    # If there is a rule defined here, the corresponding CamelCase model
    # will be indexed
    convert_rules = {
        "committee": {
            "id": "id",
            "title": "name",
            "description": ["info", "about"]
        },
        "committee_meeting": {
            "id": "id",
            "title": "title",
            "description": "summary",
            "fulltext": "body",
            "date": "date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "member": {
            "id": "id",
            "title": "name",
            "description": "bio",
            "date": "start_date",
        },
        "bill": {
            "id": "id",
            "title": "title",
            "year": "year",
            "number": "number",
            "code": "code",
        },
        "hansard": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "date",
        },
        "briefing": {
            "id": "id",
            "title": "title",
            "description": "summary",
            "fulltext": "body",
            "date": "date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "question_reply": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "tabled_committee_report": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "call_for_comment": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
            "committee_name": ["committee", "name"],
            "committee_id": ["committee", "id"],
        },
        "policy_document": {
            "id": "id",
            "title": "title",
            "date": "start_date",
        },
        "gazette": {
            "id": "id",
            "title": "title",
            "date": "start_date",
        },
        "daily_schedule": {
            "id": "id",
            "title": "title",
            "fulltext": "body",
            "date": "start_date",
        },
    }

    @classmethod
    def serialise(cls, data_type, obj):
        item = {}
        for key, field in Transforms.convert_rules[data_type].iteritems():
            val = cls.get_val(obj, field)
            if isinstance(val, unicode):
                val = BeautifulSoup(val).get_text().strip()
            item[key] = val
        return item

    @classmethod
    def get_val(cls, obj, field):
        if isinstance(field, list):
            if (len(field) == 1):
                if hasattr(obj, field[0]):
                    return getattr(obj, field[0])
            key = field[:1][0]
            if isinstance(key, int):
                if len(obj) > key:
                    return cls.get_val(obj[key], field[1:])
                return None
            if hasattr(obj, key):
                newobj = getattr(obj, key)
                return cls.get_val(newobj, field[1:])
            else:
                return None
        else:
            return getattr(obj, field)



if __name__ == "__main__":
    # print "ElasticSearch PMG library"
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
