import os
import platform
if platform.system() == "Windows":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env.local", override=True)
    print("✅ Loaded .env file (Windows detected)")
    
from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from redis import Redis
from minio import Minio

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
jwt = JWTManager()
cors = CORS()
redis_client = None
minio_client = None

def create_app(config_class=Config):
    global redis_client, minio_client
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Debug: Print startup configuration (mask sensitive values)
    print("=" * 60)
    print("🚀 DOTS BACKEND STARTING UP")
    print("=" * 60)
    print(f"DATABASE_URL: {'✅ SET' if app.config.get('SQLALCHEMY_DATABASE_URI') else '❌ NOT SET'}")
    print(f"REDIS_URL: {'✅ SET' if app.config.get('REDIS_URL') else '❌ NOT SET'}")
    print(f"SECRET_KEY: {'✅ SET' if app.config.get('SECRET_KEY') else '❌ NOT SET'}")
    print(f"JWT_SECRET_KEY: {'✅ SET' if app.config.get('JWT_SECRET_KEY') else '❌ NOT SET'}")
    print(f"SENDGRID_API_KEY: {'✅ SET' if app.config.get('SENDGRID_API_KEY') else '❌ NOT SET'}")
    print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER', '❌ NOT SET')}")
    print(f"MINIO_ENDPOINT: {app.config.get('MINIO_ENDPOINT', '❌ NOT SET')}")
    print(f"MINIO_PUBLIC_ENDPOINT: {app.config.get('MINIO_PUBLIC_ENDPOINT', '❌ NOT SET')}")
    print(f"CURRENT_DOMAIN: {app.config.get('CURRENT_DOMAIN', '❌ NOT SET')}")
    print(f"ALLOWED_ORIGINS: {os.environ.get('ALLOWED_ORIGINS', '*')}")
    print("=" * 60)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)
    # CORS Configuration
    # In production, replace '*' with your actual frontend domains
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
    cors.init_app(app, resources={
        r"/auth/*": {"origins": allowed_origins},
        r"/mobile/*": {"origins": allowed_origins},
        r"/pi/*": {"origins": allowed_origins},
        r"/social/*": {"origins": allowed_origins}
    })

    # Initialize Redis client
    try:
        if not app.config.get('REDIS_URL'):
            raise ValueError("REDIS_URL environment variable is not set!")
        
        redis_client = Redis.from_url(
            app.config['REDIS_URL'],
            decode_responses=True  # Crucial for working with strings
        )
        redis_client.ping()
        app.logger.info("✅ Connected to Redis successfully!")
    except Exception as e:
        app.logger.error(f"❌ Failed to connect to Redis: {e}")
        app.logger.error("Make sure Redis service is added in Railway and REDIS_URL is set")

    # Initialize Minio client
    try:
        # Validate MinIO configuration
        required_minio_vars = ['MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY']
        missing_vars = [var for var in required_minio_vars if not app.config.get(var)]
        
        if missing_vars:
            raise ValueError(f"Missing MinIO configuration: {', '.join(missing_vars)}")
        
        minio_client = Minio(
            app.config['MINIO_ENDPOINT'],
            access_key=app.config['MINIO_ACCESS_KEY'],
            secret_key=app.config['MINIO_SECRET_KEY'],
            secure=app.config['MINIO_SECURE']
        )
        app.logger.info("✅ Connected to Minio successfully!")
        
        # Initialize bucket at startup
        from app.services.minio_service import initialize_minio_bucket
        with app.app_context():
            if initialize_minio_bucket():
                app.logger.info("✅ Minio bucket initialized successfully!")
            else:
                app.logger.warning("⚠️ Minio bucket initialization had issues, but continuing...")
                
    except Exception as e:
        app.logger.error(f"❌ Failed to connect to Minio: {e}")
        app.logger.error("Set MINIO_PRIVATE_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD in Railway")

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.mobile_api import mobile_bp
    from app.routes.pi_api import pi_bp
    from app.routes.social_api import social_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(mobile_bp, url_prefix='/mobile')
    app.register_blueprint(pi_bp, url_prefix='/pi')
    app.register_blueprint(social_bp, url_prefix='/social')

    # Health check endpoint for Railway and monitoring
    @app.route('/')
    @app.route('/health')
    def health_check():
        return {
            "status": "healthy",
            "service": "dots-backend",
            "version": "1.0.0"
        }, 200

    return app

