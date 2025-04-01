import os

class Config:
    # MySQL Configuration
    MYSQL_HOST = '127.0.0.1'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'root'
    MYSQL_DB = 'user_database'

    # File upload configuration
    UPLOAD_FOLDER = 'cart/static/images/products'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Admin credentials (in a real app, this should be in a database with hashed passwords)
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

    # Blueprint configuration
    BLUEPRINT_NAME = 'cart'
    BLUEPRINT_URL_PREFIX = '/cart'
    BLUEPRINT_TEMPLATE_FOLDER = 'templates'
    BLUEPRINT_STATIC_FOLDER = 'static'
    
    # Flask secret key
    SECRET_KEY = 'your-secret-key-here'  # Change this to a secure secret key in production 