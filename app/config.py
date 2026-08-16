import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Domain Configuration (for email links, etc.)
    # In production on Railway, this will be auto-set by RAILWAY_PUBLIC_DOMAIN
    # or you can manually set CURRENT_DOMAIN
    CURRENT_DOMAIN = os.environ.get('CURRENT_DOMAIN') or \
                     os.environ.get('RAILWAY_PUBLIC_DOMAIN') or \
                     'localhost:8080'
    
    # PostgreSQL (using Railway's provided var)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis (using Railway's provided var)
    REDIS_URL = os.environ.get('REDIS_URL')
    SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

    # Minio (using Railway's provided vars)
    MINIO_ENDPOINT = os.environ.get('MINIO_PRIVATE_ENDPOINT', '').replace('http://', '')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ROOT_USER')
    MINIO_SECRET_KEY = os.environ.get('MINIO_ROOT_PASSWORD')
    MINIO_PUBLIC_ENDPOINT = os.environ.get('MINIO_PUBLIC_ENDPOINT')  # For generating public URLs
    MINIO_BUCKET_NAME = "photobooth"
    # Note: MINIO_PRIVATE_ENDPOINT is http, so secure=False
    MINIO_SECURE = False

    # SendGrid (Flask-Mail)
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    MAIL_SERVER = 'smtp.sendgrid.net'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'apikey'
    MAIL_PASSWORD = SENDGRID_API_KEY
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@photobooth.app')

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    # Access tokens expire after 24 hours
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_ACCESS_TOKEN_HOURS', 24)))
    # Refresh tokens expire after 30 days
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_DAYS', 30)))

    # Email Verification
    # Set to "True" to require email verification before login, "False" to disable
    VERIFY_EMAILS = os.environ.get('VERIFY_EMAILS', 'True').lower() == 'true'

