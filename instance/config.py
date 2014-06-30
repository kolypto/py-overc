DEBUG = True
TESTING = False

# Server settings
SERVER_NAME = None
APPLICATION_ROOT = None
PREFERRED_URL_SCHEME = 'http'
SECRET_KEY='<something-secret>'

# Session cookies
SESSION_COOKIE_NAME = 'dpsession'
PERMANENT_SESSION_LIFETIME = 86400

# Uploads
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16777216

# Database connection string
DB_CONNECT = 'mysql://user:pass@127.0.0.1/overc'

# Alert destinations: { name: (command, command-arguments...) }
ALERTS = {
    'test': ('fwrite.sh', '/tmp/testfile.txt'),
}
