from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
import MySQLdb.cursors
import logging

class Product:
    def __init__(self, mysql):
        self.mysql = mysql
        self.UPLOAD_FOLDER = 'cart/static/images/products'
        self.ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.logger = logging.getLogger(__name__)

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def save_image(self, file, category, app_root_path):
        """Save image and return the URL path"""
        try:
            if file and self.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                
                # Create category directory if it doesn't exist
                category_path = os.path.join(app_root_path, self.UPLOAD_FOLDER, category.lower())
                self.logger.info(f"Creating directory at: {category_path}")
                os.makedirs(category_path, exist_ok=True)
                
                # Save the file
                filepath = os.path.join(category_path, filename)
                self.logger.info(f"Saving file to: {filepath}")
                file.save(filepath)
                
                # Return URL path
                image_url = f"/cart/static/images/products/{category.lower()}/{filename}"
                self.logger.info(f"Image URL set to: {image_url}")
                return image_url
            else:
                self.logger.error("Invalid file or file type")
                return None
        except Exception as e:
            self.logger.error(f"Error saving image: {str(e)}")
            raise e

    def get_all_products(self, category=None):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            if category and category != 'all':
                cursor.execute('''
                    SELECT p.*, c.name as category_name,
                           GROUP_CONCAT(DISTINCT hf.name) as health_restrictions,
                           GROUP_CONCAT(DISTINCT pt.tag) as tags
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    LEFT JOIN product_health_restrictions phr ON p.id = phr.product_id
                    LEFT JOIN health_filters hf ON phr.filter_id = hf.id
                    LEFT JOIN product_tags pt ON p.id = pt.product_id
                    WHERE c.name = %s
                    GROUP BY p.id
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT p.*, c.name as category_name,
                           GROUP_CONCAT(DISTINCT hf.name) as health_restrictions,
                           GROUP_CONCAT(DISTINCT pt.tag) as tags
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    LEFT JOIN product_health_restrictions phr ON p.id = phr.product_id
                    LEFT JOIN health_filters hf ON phr.filter_id = hf.id
                    LEFT JOIN product_tags pt ON p.id = pt.product_id
                    GROUP BY p.id
                ''')
            
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

    def get_product_by_id(self, product_id):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('''
                SELECT p.*, c.name as category_name,
                       GROUP_CONCAT(DISTINCT hf.name) as health_restrictions,
                       GROUP_CONCAT(DISTINCT pt.tag) as tags
                FROM products p
                JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_health_restrictions phr ON p.id = phr.product_id
                LEFT JOIN health_filters hf ON phr.filter_id = hf.id
                LEFT JOIN product_tags pt ON p.id = pt.product_id
                WHERE p.id = %s
                GROUP BY p.id
            ''', (product_id,))
            product = cursor.fetchone()
            # Ensure tags and health_restrictions are never None to prevent split errors
            if product:
                if product.get('tags') is None:
                    product['tags'] = ''
                if product.get('health_restrictions') is None:
                    product['health_restrictions'] = ''
            return product
        finally:
            cursor.close()

    def add_product(self, form_data, file, app_root_path):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            self.logger.info(f"Adding new product: {form_data['name']}")
            
            # Get category ID
            cursor.execute('SELECT id FROM categories WHERE name = %s', (form_data['category'],))
            category_result = cursor.fetchone()
            if not category_result:
                self.logger.error(f"Category '{form_data['category']}' not found")
                raise ValueError(f"Category '{form_data['category']}' not found")
            category_id = category_result['id']
            self.logger.info(f"Found category ID: {category_id}")
            
            # Handle image upload
            image_url = self.save_image(file, form_data['category'], app_root_path)
            if not image_url:
                self.logger.error("Failed to save image")
                raise ValueError('Invalid file type or no file provided')

            # Insert product
            self.logger.info("Inserting product into database")
            cursor.execute('''
                INSERT INTO products (category_id, name, price, weight, image_url, fat, sugars, sodium)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                category_id,
                form_data['name'],
                float(form_data['price']),
                form_data['weight'],
                image_url,
                float(form_data['fat']),
                float(form_data['sugars']),
                float(form_data['sodium'])
            ))
            product_id = cursor.lastrowid
            self.logger.info(f"Product inserted with ID: {product_id}")

            # Add health restrictions
            health_restrictions = []
            if form_data.get('not_for_diabetes'): health_restrictions.append('diabetes')
            if form_data.get('not_for_heart'): health_restrictions.append('heart')
            if form_data.get('not_for_obesity'): health_restrictions.append('obesity')
            if form_data.get('not_for_hypertension'): health_restrictions.append('hypertension')

            self.logger.info(f"Adding health restrictions: {health_restrictions}")
            for restriction in health_restrictions:
                cursor.execute('''
                    INSERT INTO product_health_restrictions (product_id, filter_id)
                    SELECT %s, id FROM health_filters WHERE name = %s
                ''', (product_id, restriction))

            # Add tags
            tags = form_data.getlist('tags') if hasattr(form_data, 'getlist') else []
            if not tags and form_data.get('tags'):
                if form_data.get('tags') is not None:
                    tags = [tag.strip() for tag in form_data.get('tags').split(',') if tag.strip()]
            
            self.logger.info(f"Adding tags: {tags}")
            for tag in tags:
                if tag:  # Only insert non-empty tags
                    cursor.execute('INSERT INTO product_tags (product_id, tag) VALUES (%s, %s)',
                                 (product_id, tag))

            self.mysql.connection.commit()
            self.logger.info("Product added successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error adding product: {str(e)}")
            self.mysql.connection.rollback()
            raise e
        finally:
            cursor.close()

    def update_product(self, product_id, form_data, file, app_root_path):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            self.logger.info(f"Updating product {product_id}")
            
            # Get current product data
            cursor.execute('''
                SELECT c.name as category_name, p.image_url 
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
            ''', (product_id,))
            current_data = cursor.fetchone()
            if not current_data:
                self.logger.error(f"Product {product_id} not found")
                raise ValueError(f"Product {product_id} not found")
            
            self.logger.info(f"Current product data: {current_data}")
            
            # Handle image upload if new file provided
            if file and file.filename:
                # Delete old image if it exists
                if current_data['image_url']:
                    old_image_path = os.path.join(app_root_path, current_data['image_url'].lstrip('/'))
                    self.logger.info(f"Attempting to delete old image: {old_image_path}")
                    try:
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                            self.logger.info("Old image deleted successfully")
                    except Exception as e:
                        self.logger.error(f"Error deleting old image: {str(e)}")

                # Save new image
                category = form_data.get('category', current_data['category_name'])
                image_url = self.save_image(file, category, app_root_path)
                if image_url:
                    cursor.execute('UPDATE products SET image_url = %s WHERE id = %s',
                                 (image_url, product_id))

            # Update other product data
            self.logger.info("Updating product details")
            cursor.execute('''
                UPDATE products
                SET name = %s, price = %s, weight = %s,
                    fat = %s, sugars = %s, sodium = %s
                WHERE id = %s
            ''', (
                form_data['name'],
                float(form_data['price']),
                form_data['weight'],
                float(form_data['fat']),
                float(form_data['sugars']),
                float(form_data['sodium']),
                product_id
            ))

            # Update health restrictions
            cursor.execute('DELETE FROM product_health_restrictions WHERE product_id = %s', (product_id,))
            health_restrictions = []
            if form_data.get('not_for_diabetes'): health_restrictions.append('diabetes')
            if form_data.get('not_for_heart'): health_restrictions.append('heart')
            if form_data.get('not_for_obesity'): health_restrictions.append('obesity')
            if form_data.get('not_for_hypertension'): health_restrictions.append('hypertension')

            self.logger.info(f"Updating health restrictions: {health_restrictions}")
            for restriction in health_restrictions:
                cursor.execute('''
                    INSERT INTO product_health_restrictions (product_id, filter_id)
                    SELECT %s, id FROM health_filters WHERE name = %s
                ''', (product_id, restriction))

            # Update tags
            cursor.execute('DELETE FROM product_tags WHERE product_id = %s', (product_id,))
            tags = form_data.getlist('tags') if hasattr(form_data, 'getlist') else []
            if not tags and form_data.get('tags'):
                # Handle case where tags might be a string
                if form_data.get('tags') is not None:
                    tags = [tag.strip() for tag in form_data.get('tags').split(',') if tag.strip()]
            
            self.logger.info(f"Updating tags: {tags}")
            for tag in tags:
                if tag:  # Only insert non-empty tags
                    cursor.execute('INSERT INTO product_tags (product_id, tag) VALUES (%s, %s)',
                                 (product_id, tag))

            self.mysql.connection.commit()
            self.logger.info("Product updated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error updating product: {str(e)}")
            self.mysql.connection.rollback()
            raise e
        finally:
            cursor.close()

    def delete_product(self, product_id, app_root_path):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            # Get image URL before deleting
            cursor.execute('SELECT image_url FROM products WHERE id = %s', (product_id,))
            product = cursor.fetchone()
            if product:
                # Delete image file
                image_path = os.path.join(app_root_path, product['image_url'].lstrip('/'))
                if os.path.exists(image_path):
                    os.remove(image_path)

                # Delete product (cascade will handle related records)
                cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
                self.mysql.connection.commit()
                return True
            return False
        except Exception as e:
            self.mysql.connection.rollback()
            raise e
        finally:
            cursor.close() 