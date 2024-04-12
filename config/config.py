from os import environ as env
import datetime
import pytz

# dev mode?
DEBUG = env.get("FLASK_ENV", "development") != "production"
TEST = env.get("FLASK_ENV") == "test"

DEBUG_CACHE = env.get("FLASK_DEBUG_CACHE", "false") == "true"
CACHE_REDIS_URL = env.get("REDIS_URL", "redis://redis:6379/0")

RUN_PERIODIC_TASKS = env.get("RUN_PERIODIC_TASKS") == "true"

WTF_CSRF_ENABLED = False if TEST else True
SECRET_KEY = env.get("FLASK_SECRET_KEY", "NSTHNSTHaoensutCGSRCGnsthoesucgsrSNTH")
GOOGLE_ANALYTICS_ID = env.get("GOOGLE_ANALYTICS_ID", None)
GOOGLE_ANALYTICS_API_SECRET = env.get("GOOGLE_ANALYTICS_API_SECRET", None)
GOOGLE_TAG_MANAGER_ID = env.get("GOOGLE_TAG_MANAGER_ID", None)

SQLALCHEMY_DATABASE_URI = env.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://pmg:pmg@localhost/pmg_test?client_encoding=utf8"
    if TEST
    else "postgresql+psycopg2://pmg:pmg@localhost/pmg?client_encoding=utf8",
)

SQLALCHEMY_ECHO = False
# This is required only be pmg.models.resources.delete_file_from_s3 and can de turned off if
# that is changed to use sqlalchemy events
SQLALCHEMY_TRACK_MODIFICATIONS = True

SQLALCHEMY_POOL_SIZE = int(env.get("SQLALCHEMY_POOL_SIZE", "10"))

RESULTS_PER_PAGE = 50
# The V2 API can support much higher volumes because callers
# can choose the fields they want
RESULTS_PER_PAGE_V2 = 500

# Premium content before this date is free
# Calculated as 1 of last year
PREMIUM_FREE_BEFORE = datetime.datetime(
    datetime.datetime.today().year - 1, 1, 1, tzinfo=pytz.utc
)

ES_SERVER = env.get("ES_SERVER", "http://localhost:9200")
SEARCH_REINDEX_CHANGES = not DEBUG  # reindex changes to models
SEARCH_RESULTS_PER_PAGE = 20

SOUNDCLOUD_APP_KEY_ID = env.get("SOUNDCLOUD_APP_KEY_ID", "")
SOUNDCLOUD_APP_KEY_SECRET = env.get("SOUNDCLOUD_APP_KEY_SECRET", "")
SOUNDCLOUD_USERNAME = env.get("SOUNDCLOUD_USERNAME", "")
SOUNDCLOUD_PASSWORD = env.get("SOUNDCLOUD_PASSWORD", "")

MAX_SOUNDCLOUD_BATCH = int(env.get("MAX_SOUNDCLOUD_BATCH", "1"))
MAX_SOUNDCLOUD_RETRIES = int(env.get("MAX_SOUNDCLOUD_RETRIES", "3"))
SOUNDCLOUD_PERIOD_HOURS = env.get("SOUNDCLOUD_PERIOD_HOURS", "6")

S3_BUCKET = env.get("S3_BUCKET", "pmg-assets")
STATIC_HOST = env.get(
    "STATIC_HOST", "http://%s.s3-website-eu-west-1.amazonaws.com/" % S3_BUCKET
)
UPLOAD_PATH = "/tmp/pmg_upload/"

if DEBUG:
    RECAPTCHA_PUBLIC_KEY = env.get(
        "RECAPTCHA_PUBLIC_KEY", "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
    )
    RECAPTCHA_PRIVATE_KEY = env.get(
        "RECAPTCHA_PRIVATE_KEY", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
    )
else:
    RECAPTCHA_PUBLIC_KEY = env.get("RECAPTCHA_PUBLIC_KEY")
    RECAPTCHA_PRIVATE_KEY = env.get("RECAPTCHA_PRIVATE_KEY")

# must match client_max_body_size in nginx.conf
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # size cap on uploads

# uploadable files
ALLOWED_EXTENSIONS = set(
    [
        "doc",
        "docx",
        "gif",
        "jpg",
        "jpeg",
        "mp3",
        "pdf",
        "png",
        "ppt",
        "pptx",
        "rtf",
        "txt",
        "wav",
        "xls",
        "xlsx",
    ]
)

# Sendgrid
SENDGRID_API_KEY = env.get("SENDGRID_API_KEY")
SENDGRID_TRANSACTIONAL_TEMPLATE_ID = "2ef9656f-db37-4072-9ed8-449368b73617"

# Flask-Mail
MAIL_SERVER = env.get("MAIL_SERVER", "smtp.sendgrid.com")
MAIL_PORT = int(env.get("MAIL_PORT", "465"))
MAIL_USE_SSL = env.get("MAIL_USE_SSL", "true") == "true"
MAIL_USERNAME = env.get("MAIL_USERNAME", "apikey")
MAIL_PASSWORD = env.get("MAIL_PASSWORD", SENDGRID_API_KEY)
MAIL_DEFAULT_SENDER = '"PMG Subscriptions" <subscribe@pmg.org.za>'

# Flask-Security config
SECURITY_URL_PREFIX = "/user"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = env.get(
    "SECURITY_PASSWORD_SALT", "ioaefroijaAMELRK#$(aerieuh984akef#$graerj"
)
SECURITY_EMAIL_SENDER = MAIL_DEFAULT_SENDER
SECURITY_TOKEN_AUTHENTICATION_HEADER = "Authentication-Token"

# Flask-Security URLs, overridden because they don't put a / at the end
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"
SECURITY_CHANGE_URL = "/change-password/"
SECURITY_RESET_URL = (
    "/forgot-password"  # Trailing slash here was causing double slash in URLs in emails
)
SECURITY_REGISTER_URL = "/register/"

# Flask-Security email subject lines
SECURITY_EMAIL_SUBJECT_REGISTER = (
    "Please confirm your email address to complete PMG signup"
)
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = (
    "Password reset instructions for your PMG account"
)
SECURITY_EMAIL_SUBJECT_CONFIRM = "Email address confirmation for your PMG account"

# Flask-Security features
SECURITY_CONFIRMABLE = True
SECURITY_LOGIN_WITHOUT_CONFIRMATION = True
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TRACKABLE = True
SECURITY_CHANGEABLE = True

SERVER_NAME = env.get("SERVER_NAME", "pmg.test:5000")
FRONTEND_HOST = env.get("FRONTEND_HOST", "http://pmg.test:5000/")
SESSION_COOKIE_DOMAIN = env.get("SESSION_COOKIE_DOMAIN", "pmg.test")
