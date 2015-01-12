DEBUG = True
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://pmg:pmg@localhost/pmg'
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.dev:5001/"
FRONTEND_HOST = "http://pmg.dev:5000/"
SESSION_COOKIE_DOMAIN = "pmg.dev"
RESULTS_PER_PAGE = 50
SQLALCHEMY_ECHO = False
STATIC_HOST = "http://eu-west-1-pmg.s3-website-eu-west-1.amazonaws.com/"
ES_SERVER = "http://ec2-54-77-69-243.eu-west-1.compute.amazonaws.com:9200"
SEARCH_REINDEX_CHANGES = False # don't reindex changes to models
S3_BUCKET = "eu-west-1-pmg"
UPLOAD_PATH = "/tmp/pmg_upload/"
ES_SERVER = "http://localhost:9200"
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

# Flask-Mail
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = "pmgorg.noreply@gmail.com"
MAIL_PASSWORD = "agoaiejlagrAIERJaerknj"
MAIL_DEFAULT_SENDER = "pmgorg.noreply@gmail.com"

# Flask-Security config
SECURITY_HOST = FRONTEND_HOST
SECURITY_URL_PREFIX = "/security"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "ioaefroijaAMELRK#$(aerieuh984akef#$graerj"
SECURITY_EMAIL_SENDER = "pmgorg.noreply@gmail.com"
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
