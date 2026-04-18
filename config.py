import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "19ae48a3c64236d6e6a2f558eb8e171a")
    # The @ symbol in the password must be URL-encoded as %40 to prevent connection errors
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://root:KARINA%402609@localhost/ambica_store")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Pool settings to prevent 'MySQL server has gone away' issues
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    
    # Advanced security & application settings
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    EMPLOYEE_SECRET_KEY = 'Ambica_Store_1983'