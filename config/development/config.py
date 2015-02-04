from os import environ as env

DEBUG = True
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://pmg:pmg@localhost/pmg?client_encoding=utf8'
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.dev:5001/"
FRONTEND_HOST = "http://pmg.dev:5000/"
SESSION_COOKIE_DOMAIN = "pmg.dev"
RESULTS_PER_PAGE = 50
SQLALCHEMY_ECHO = False
S3_BUCKET = "pmg-assets"
STATIC_HOST = "http://%s.s3-website-eu-west-1.amazonaws.com/" % S3_BUCKET
ES_SERVER = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
SEARCH_REINDEX_CHANGES = False # don't reindex changes to models
UPLOAD_PATH = "/tmp/pmg_upload/"
ES_SERVER = "http://localhost:9200"
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # size cap on uploads
ALLOWED_EXTENSIONS = set(
    [
        "doc",
        "docx",
        "jpg",
        "jpeg",
        "mp3",
        "pdf",
        "ppt",
        "pptx",
        "rtf",
        "txt",
        "wav",
        "xls",
        "xlsx",
    ]
)

# Mandrill
MANDRILL_API_KEY = env.get('MAIL_PASSWORD')
MANDRILL_TRANSACTIONAL_SUBACCOUNT = 'transactional'
MANDRILL_ALERTS_SUBACCOUNT = 'alerts'

# Flask-Mail
MAIL_SERVER = 'smtp.mandrillapp.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'webapps+pmg@code4sa.org'
MAIL_PASSWORD = MANDRILL_API_KEY
MAIL_DEFAULT_SENDER = '"PMG Subscriptions" <subscribe@pmg.org.za>'

# Flask-Security config
SECURITY_HOST = FRONTEND_HOST
SECURITY_URL_PREFIX = "/security"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = env.get('SECURITY_PASSWORD_SALT', "ioaefroijaAMELRK#$(aerieuh984akef#$graerj")
SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER
SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"
SECURITY_POST_LOGIN_VIEW = "/admin"
SECURITY_POST_LOGOUT_VIEW = "/admin"

# Flask-Security email subject lines
SECURITY_EMAIL_SUBJECT_REGISTER = "Welcome to the Parliamentary Monitoring Group"
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = "Password reset instructions for your PMG account"

# Flask-Security features
SECURITY_CONFIRMABLE = True
SECURITY_LOGIN_WITHOUT_CONFIRMATION = True
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TRACKABLE = True
SECURITY_CHANGEABLE = True

# enable CSRF only for the frontend. The backend must have it disable so that Flask-Security can be used as an API
import os
WTF_CSRF_ENABLED = os.environ.get('PMG_LAYER') == 'frontend'
