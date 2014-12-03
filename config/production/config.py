from os import environ as env

SQLALCHEMY_DATABASE_URI = env['SQLALCHEMY_DATABASE_URI']
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.org.za/"
FRONTEND_HOST = "http://new.pmg.org.za/"
RESULTS_PER_PAGE = 20

STATIC_HOST = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/"
ES_SERVER = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
