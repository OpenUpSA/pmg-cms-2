LOG_LEVEL = "DEBUG"
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/tmp.db'
LOGGER_NAME = "pmg_cms_logger"  # make sure this is not the same as the name of the package to avoid conflicts with Flask's own logger
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://localhost:5001/"
RESULTS_PER_PAGE = 50

STATIC_HOST = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/"