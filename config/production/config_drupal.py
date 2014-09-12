LOG_LEVEL = "DEBUG"
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/tmp_drupal.db'
LOGGER_NAME = "pmg_cms_logger"  # make sure this is not the same as the name of the package to avoid conflicts with Flask's own logger
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "0.0.0.0:5005"
RESULTS_PER_PAGE = 20