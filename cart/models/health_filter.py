from flask_mysqldb import MySQL
import MySQLdb.cursors

class HealthFilter:
    def __init__(self, mysql):
        self.mysql = mysql

    def get_all_filters(self):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('SELECT name FROM health_filters')
            return [filter['name'] for filter in cursor.fetchall()]
        finally:
            cursor.close()

    def get_filter_id(self, filter_name):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('SELECT id FROM health_filters WHERE name = %s', (filter_name,))
            result = cursor.fetchone()
            return result['id'] if result else None
        finally:
            cursor.close()

    def get_health_stats(self):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('''
                SELECT hf.name, COUNT(phr.product_id) as product_count
                FROM health_filters hf
                LEFT JOIN product_health_restrictions phr ON hf.id = phr.filter_id
                GROUP BY hf.name
            ''')
            return cursor.fetchall()
        finally:
            cursor.close() 