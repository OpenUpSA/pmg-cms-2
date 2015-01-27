from os import environ as env

SQLALCHEMY_DATABASE_URI = env['SQLALCHEMY_DATABASE_URI']
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.org.za/"
FRONTEND_HOST = "https://new.pmg.org.za/"
SESSION_COOKIE_DOMAIN = "pmg.org.za"
RESULTS_PER_PAGE = 20

STATIC_HOST = "http://pmg-assets.s3-eu-west-1.amazonaws.com/"
ES_SERVER = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
SEARCH_REINDEX_CHANGES = True # reindex changes to models
S3_BUCKET = "eu-west-1-pmg"
UPLOAD_PATH = "/tmp/pmg_upload/"
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # size cap on uploads
ALLOWED_EXTENSIONS = set(
    [
        "doc",
        "jpg",
        "jpeg",
        "mp3",
        "pdf",
        "ppt",
        "rtf",
        "txt",
        "wav",
        "xls",
    ]
)

# Mandrill
MANDRILL_API_KEY = env.get('MAIL_PASSWORD')

# Flask-Mail
MAIL_SERVER = 'smtp.mandrillapp.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'webapps+pmg@code4sa.org'
MAIL_PASSWORD = MANDRILL_API_KEY
MAIL_DEFAULT_SENDER = "subscribe@pmg.org.za"

# Flask-Security config
SECURITY_HOST = FRONTEND_HOST
SECURITY_URL_PREFIX = "/security"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = env['SECURITY_PASSWORD_SALT']
SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER
SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"
SECURITY_POST_LOGIN_VIEW = "/admin"
SECURITY_POST_LOGOUT_VIEW = "/admin"

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
