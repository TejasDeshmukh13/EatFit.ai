from flask_mysqldb import MySQL
import MySQLdb.cursors

class Category:
    def __init__(self, mysql):
        self.mysql = mysql

    def get_all_categories(self):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('SELECT name FROM categories')
            return [category['name'] for category in cursor.fetchall()]
        finally:
            cursor.close()

    def get_category_id(self, category_name):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('SELECT id FROM categories WHERE name = %s', (category_name,))
            result = cursor.fetchone()
            return result['id'] if result else None
        finally:
            cursor.close()

    def get_products_by_category(self, category_name):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('''
                SELECT p.*, GROUP_CONCAT(DISTINCT hf.name) as health_restrictions,
                       GROUP_CONCAT(DISTINCT pt.tag) as tags
                FROM products p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_health_restrictions phr ON p.id = phr.product_id
                LEFT JOIN health_filters hf ON phr.filter_id = hf.id
                LEFT JOIN product_tags pt ON p.id = pt.product_id
                WHERE c.name = %s
                GROUP BY p.id
            ''', (category_name,))
            
            products = cursor.fetchall()
            
            # Ensure tags and health_restrictions are never None to prevent split errors
            for product in products:
                if product.get('tags') is None:
                    product['tags'] = ''
                if product.get('health_restrictions') is None:
                    product['health_restrictions'] = ''
                    
            return products
        finally:
            cursor.close()

    def edit_category(self, old_name, new_name):
        """Edit a category name"""
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            # Check if new name already exists
            cursor.execute('SELECT id FROM categories WHERE name = %s', (new_name,))
            if cursor.fetchone():
                raise ValueError(f"Category '{new_name}' already exists")

            # Get all products in this category to update their image paths
            cursor.execute('SELECT id, image_url FROM products WHERE category_id = (SELECT id FROM categories WHERE name = %s)', (old_name,))
            products = cursor.fetchall()

            # Update category name
            cursor.execute('UPDATE categories SET name = %s WHERE name = %s', (new_name, old_name))

            # Update image paths for all products in this category
            for product in products:
                if product['image_url']:
                    new_image_url = product['image_url'].replace(f'/products/{old_name}/', f'/products/{new_name}/')
                    cursor.execute('UPDATE products SET image_url = %s WHERE id = %s', 
                                 (new_image_url, product['id']))

            self.mysql.connection.commit()
            return True
        except Exception as e:
            self.mysql.connection.rollback()
            raise e
        finally:
            cursor.close() 