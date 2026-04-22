import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "19ae48a3c64236d6e6a2f558eb8e171a")
    # Render automatically sets RENDER=true. If on Render, use the permanent PostgreSQL Database.
    if os.environ.get("RENDER"):
        SQLALCHEMY_DATABASE_URI = "postgresql://ambicastore_db_user:a94GXbPfzGhpMLAK9uAj9spS1m0Ii0t7@dpg-d7icpqosfn5c738hhfp0-a/ambicastore_db"
    else:
        # Local MySQL Configuration (to satisfy Faculty requirement)
        # MAKE SURE your MySQL server (like XAMPP) is running!
        # And create a database named 'ambica_store' in phpMyAdmin before running the app.
        SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:KARINA%402609@localhost/ambica_store"
        
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