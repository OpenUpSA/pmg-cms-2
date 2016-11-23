from os import environ as env

# dev mode?
DEBUG = env.get('FLASK_ENV', 'development') != 'production'

RUN_PERIODIC_TASKS = env.get('RUN_PERIODIC_TASKS') == 'true'

WTF_CSRF_ENABLED = True
SECRET_KEY = env.get('FLASK_SECRET_KEY', "NSTHNSTHaoensutCGSRCGnsthoesucgsrSNTH")
GOOGLE_ANALYTICS_ID = 'UA-10305579-1'

SQLALCHEMY_DATABASE_URI = env.get('SQLALCHEMY_DATABASE_URI', 'postgresql+psycopg2://pmg:pmg@localhost/pmg?client_encoding=utf8')
SQLALCHEMY_ECHO = DEBUG

RESULTS_PER_PAGE = 50

ES_SERVER = env.get("ES_SERVER", 'http://localhost:9200')
SEARCH_REINDEX_CHANGES = not DEBUG  # reindex changes to models
SEARCH_RESULTS_PER_PAGE = 20

SOUNDCLOUD_APP_KEY_ID = env.get("SOUNDCLOUD_APP_KEY_ID", '')
SOUNDCLOUD_APP_KEY_SECRET = env.get("SOUNDCLOUD_APP_KEY_SECRET", '')
SOUNDCLOUD_USERNAME = env.get("SOUNDCLOUD_USERNAME", '')
SOUNDCLOUD_PASSWORD = env.get("SOUNDCLOUD_PASSWORD", '')

MAX_SOUNDCLOUD_BATCH = int(env.get("MAX_SOUNDCLOUD_BATCH", '1'))
SOUNDCLOUD_PERIOD_MINUTES = env.get("SOUNDCLOUD_PERIOD_MINUTES", '5')

S3_BUCKET = "pmg-assets"
STATIC_HOST = "http://%s.s3-website-eu-west-1.amazonaws.com/" % S3_BUCKET
UPLOAD_PATH = "/tmp/pmg_upload/"

RECAPTCHA_PUBLIC_KEY = env.get('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = env.get('RECAPTCHA_PRIVATE_KEY')

# must match client_max_body_size in nginx.conf
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # size cap on uploads

# uploadable files
ALLOWED_EXTENSIONS = set([
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
])

# Sendgrid
SENDGRID_API_KEY = env.get('SENDGRID_API_KEY')
SENDGRID_TRANSACTIONAL_TEMPLATE_ID = '2ef9656f-db37-4072-9ed8-449368b73617'

# Flask-Mail
MAIL_SERVER = 'smtp.sendgrid.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'pmg-website'
MAIL_PASSWORD = env.get('MAIL_PASSWORD')
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

# SharpSpring mailing lists
SHARPSPRING_API_KEY = env.get('SHARPSPRING_API_KEY')
SHARPSPRING_API_SECRET = env.get('SHARPSPRING_API_SECRET')

if DEBUG:
    SERVER_NAME = 'pmg.dev:5000'
    API_URL = "http://api.pmg.dev:5000/"
    FRONTEND_HOST = "http://pmg.dev:5000/"
    SESSION_COOKIE_DOMAIN = "pmg.dev"
else:
    SERVER_NAME = 'pmg.org.za'
    # Use the EC2-internal API endpoint, which doesn't trombone through the EC2
    # firewall and back in again, saving us money and msecs
    API_URL = "https://api-internal.pmg.org.za/"
    FRONTEND_HOST = "https://pmg.org.za/"
    SESSION_COOKIE_DOMAIN = "pmg.org.za"
