from os import environ as env

WTF_CSRF_ENABLED = True
SERVER_NAME = 'pmg.dev:5000'
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://pmg:pmg@localhost/pmg?client_encoding=utf8'
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.dev:5000/"
FRONTEND_HOST = "http://pmg.dev:5000/"
SESSION_COOKIE_DOMAIN = "pmg.dev"
RESULTS_PER_PAGE = 50
SEARCH_RESULTS_PER_PAGE = 20
SQLALCHEMY_ECHO = False
S3_BUCKET = "pmg-assets"
STATIC_HOST = "http://%s.s3-website-eu-west-1.amazonaws.com/" % S3_BUCKET
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

RECAPTCHA_PUBLIC_KEY = env.get('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = env.get('RECAPTCHA_PRIVATE_KEY')

# Mandrill
MANDRILL_API_KEY = env.get('MAIL_PASSWORD')
MANDRILL_TRANSACTIONAL_TEMPLATE = 'notification-template'
MANDRILL_TRANSACTIONAL_SUBACCOUNT = 'transactional'
MANDRILL_ALERTS_TEMPLATE = 'notification-template'
MANDRILL_ALERTS_SUBACCOUNT = 'alerts'

# Flask-Mail
MAIL_SERVER = 'smtp.mandrillapp.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'webapps+pmg@code4sa.org'
MAIL_PASSWORD = MANDRILL_API_KEY
MAIL_DEFAULT_SENDER = '"PMG Subscriptions" <subscribe@pmg.org.za>'

# Flask-Security config
SECURITY_URL_PREFIX = "/user"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = env.get('SECURITY_PASSWORD_SALT', "ioaefroijaAMELRK#$(aerieuh984akef#$graerj")
SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER
SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"

# Flask-Security URLs, overridden because they don't put a / at the end
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"
SECURITY_CHANGE_URL = "/change-password/"
SECURITY_RESET_URL = "/forgot-password/"
SECURITY_REGISTER_URL = "/register/"

# Flask-Security email subject lines
SECURITY_EMAIL_SUBJECT_REGISTER = "Welcome to the Parliamentary Monitoring Group"
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = "Password reset instructions for your PMG account"


# Flask-Security features
SECURITY_CONFIRMABLE = False
SECURITY_LOGIN_WITHOUT_CONFIRMATION = True
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TRACKABLE = True
SECURITY_CHANGEABLE = True
