from pyelasticsearch.client import ElasticSearch
from pmg.models import db
import os

tables = db.metadata.tables
table_name_list = tables.keys()
es = ElasticSearch(os.environ.get('ES_SERVER', 'http://localhost:9200'))

for table_name in table_name_list:
    column_name_list = tables[table_name].columns.keys()
    rows = db.session.query(tables[table_name]).all()
    for row in rows:
        json = {}
        for i in range(len(column_name_list)):
            column_name = column_name_list[i]
            value = row[i]
            json[column_name] = value
        print(json)
        es.index('pmg', table_name, doc=json)