"""
Database connection and operations.
"""
from flask import current_app, g
from flask_mysqldb import MySQL
import MySQLdb
import logging

logger = logging.getLogger(__name__)

def get_db():
    """Get the database connection."""
    if 'db' not in g:
        try:
            g.db = MySQL(current_app).connection
            g.db.ping(reconnect=True)
        except (AttributeError, MySQLdb.OperationalError) as e:
            logger.error(f"Database connection error: {str(e)}")
            # Try to reconnect with different auth plugin if needed
            if 'Authentication plugin' in str(e):
                try:
                    current_app.config['MYSQL_AUTH_PLUGIN'] = 'mysql_native_password'
                    g.db = MySQL(current_app).connection
                except Exception as e2:
                    logger.error(f"Database reconnection failed: {str(e2)}")
                    g.db = None
            else:
                g.db = None
    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except MySQLdb.OperationalError as e:
            if e.args[0] != 2006:  # Ignore "MySQL server has gone away" error
                logger.error(f"Error closing database connection: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error closing database: {str(e)}")

def init_app(app):
    """Initialize database with the application."""
    app.teardown_appcontext(close_db) 