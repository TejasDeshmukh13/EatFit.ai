from flask_mysqldb import MySQL
import MySQLdb.cursors
import logging

class BaseModel:
    def __init__(self, mysql):
        self.mysql = mysql
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_query(self, query, params=None):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            raise
        finally:
            cursor.close()

    def execute_single_query(self, query, params=None):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            raise
        finally:
            cursor.close()

    def execute_update(self, query, params=None):
        cursor = self.mysql.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.mysql.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            self.mysql.connection.rollback()
            self.logger.error(f"Error executing update: {str(e)}")
            raise
        finally:
            cursor.close()

    def begin_transaction(self):
        self.mysql.connection.begin()

    def commit_transaction(self):
        self.mysql.connection.commit()

    def rollback_transaction(self):
        self.mysql.connection.rollback() 