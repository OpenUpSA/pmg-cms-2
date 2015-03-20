from os import environ as env

WTF_CSRF_ENABLED = True
SERVER_NAME = 'pmg.org.za'
SQLALCHEMY_DATABASE_URI = env['SQLALCHEMY_DATABASE_URI']
SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"
API_HOST = "http://api.pmg.org.za/"
FRONTEND_HOST = "https://new.pmg.org.za/"
SESSION_COOKIE_DOMAIN = "pmg.org.za"
RESULTS_PER_PAGE = 50
SEARCH_RESULTS_PER_PAGE = 20

ES_SERVER = "http://ec2-54-154-176-3.eu-west-1.compute.amazonaws.com:9200"
SEARCH_REINDEX_CHANGES = True # reindex changes to models
S3_BUCKET = "pmg-assets"
STATIC_HOST = "http://%s.s3-website-eu-west-1.amazonaws.com/" % S3_BUCKET
UPLOAD_PATH = "/tmp/pmg_upload/"
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
SECURITY_URL_PREFIX = "/user"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = env['SECURITY_PASSWORD_SALT']
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
