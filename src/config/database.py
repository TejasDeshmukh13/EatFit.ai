"""
Database configuration settings.
"""

DB_CONFIG = {
    'MYSQL_HOST': '127.0.0.1',
    'MYSQL_USER': 'root',
    'MYSQL_PASSWORD': 'root',
    'MYSQL_DB': 'user_database',
    'MYSQL_AUTH_PLUGIN': 'mysql_native_password',
    'MYSQL_POOL_NAME': 'eatfit_pool',
    'MYSQL_POOL_SIZE': 32,
    'MYSQL_POOL_RESET_SESSION': True,
    'MYSQL_CONNECT_TIMEOUT': 60,
    'MYSQL_READ_TIMEOUT': 30,
    'MYSQL_WRITE_TIMEOUT': 30,
    'MYSQL_AUTOCOMMIT': True,
    'MYSQL_CHARSET': 'utf8mb4',
    'MYSQL_COLLATION': 'utf8mb4_unicode_ci',
    'MYSQL_USE_UNICODE': True,
    'MYSQL_SSL': False,
    'MYSQL_COMPRESS': False,
    'MYSQL_INIT_COMMAND': 'SET NAMES utf8mb4',
    'MYSQL_LOCAL_INFILE': False,
    'MYSQL_MAX_ALLOWED_PACKET': 16777216,  # 16MB
    'MYSQL_CONNECT_ARGS': {
        'connect_timeout': 60,
        'read_timeout': 30,
        'write_timeout': 30
    }
} 