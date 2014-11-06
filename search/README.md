# Code4SA PMG Elastic Search Integration

This package consists of a library and tools for integrating PMG with ElasticSearch. 
(Technically, it could take any API endpoint and sync to ElasticSearch.)

The primary file is the library `search.py`, as well as `test.py` for testing, and `import.py` for doing a full import of all the PMG data to ElasticSearch.

## search.py 
### Methods

| Method | Description | Parameters|
|--------|-------------|-----------|
| test 			| Runs a few tests to make sure we can connect, insert, search and delete documents | |
| import_data 	| Imports data from an api endpoint containing a specific data type into ElasticSearch 				| data_type |
| drop 			| Drops a data type 																				| data_type |
| update 		| Updates a document. It searches for 'id' to use as the id, but you can set it explicitly too 		| data_type, item, uid = False |
| insert 		| Inserts a document. It searches for 'id' to use as the id, but you can set it explicitly too 		| data_type, item, uid = False |
| delete 		| Deletes a document from ElasticSearch 															| data_type, uid |
| get 			| Gets a single document by ID 																		| data_type, uid |
| search 		| Searches across data types for the search term in fields defined by the property `search_fields` 	| query, size=10 |


### Properties

| Property 		| Description 					| Default 					|
|---------------|-------------------------------|---------------------------|
| apiserver 	| Address of the API			| "http://localhost:5001"	|
| esserver		| Address of the ES server		| "http://localhost:9200"	|
| index_name	| Default Index name			| "pmg"						|
| search_fields	| The fields we need to search	| ["name", "title"] 		|
