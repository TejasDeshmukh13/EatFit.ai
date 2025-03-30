from flask import Flask, Blueprint, render_template, jsonify, request, redirect, url_for, flash, session
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_mysqldb import MySQL
from functools import wraps
from .models import Product, Category, HealthFilter
from .config import Config

class CartBlueprint:
    def __init__(self):
        self.blueprint = Blueprint(
            Config.BLUEPRINT_NAME,
            __name__,
            template_folder=Config.BLUEPRINT_TEMPLATE_FOLDER,
            static_folder=Config.BLUEPRINT_STATIC_FOLDER,
            url_prefix=Config.BLUEPRINT_URL_PREFIX
        )
        
        # Initialize MySQL
        self.mysql = MySQL()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Register routes
        self.register_routes()
    
    def register_routes(self):
        """Register all routes with the blueprint"""
        # Main routes
        self.blueprint.add_url_rule('/', 'index', self.index)
        
        # Admin routes
        self.blueprint.add_url_rule('/admin', 'admin', self.admin, methods=['GET'])
        self.blueprint.add_url_rule('/admin/login', 'admin_login', self.admin_login, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/admin/logout', 'admin_logout', self.admin_logout)
        self.blueprint.add_url_rule('/admin/products', 'admin_products', self.admin_products)
        self.blueprint.add_url_rule('/admin/product/add', 'add_product', self.add_product, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/admin/product/edit/<int:product_id>', 'edit_product', self.edit_product, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/admin/product/delete/<int:product_id>', 'delete_product', self.delete_product, methods=['POST'])
        
        # Category routes
        self.blueprint.add_url_rule('/admin/categories', 'admin_categories', self.admin_categories)
        self.blueprint.add_url_rule('/admin/category/edit/<category_name>', 'edit_category', self.edit_category, methods=['GET', 'POST'])
        
        # Category display routes
        self.blueprint.add_url_rule('/snacks', 'snacks', self.snacks)
        self.blueprint.add_url_rule('/breakfast', 'breakfast', self.breakfast)
        self.blueprint.add_url_rule('/chocolates', 'chocolates', self.chocolates)
        self.blueprint.add_url_rule('/cold-drinks-and-juices', 'cold_drinks', self.cold_drinks)
        self.blueprint.add_url_rule('/drinks', 'drinks', self.drinks)
        self.blueprint.add_url_rule('/dairy', 'dairy', self.dairy)
        self.blueprint.add_url_rule('/instant', 'instant', self.instant)
        self.blueprint.add_url_rule('/groceries', 'groceries', self.groceries)
        self.blueprint.add_url_rule('/supplements', 'supplements', self.supplements)
    
    def login_required(self, f):
        """Decorator to require admin login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                flash('Please log in first', 'error')
                return redirect(url_for('cart.admin_login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Route handlers
    def index(self):
        """Main catalog page"""
        return render_template('categories.html')
    
    def admin(self):
        """Admin dashboard"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            product_model = Product(self.mysql)
            category_model = Category(self.mysql)
            health_filter_model = HealthFilter(self.mysql)
            
            # Get statistics
            products = product_model.get_all_products()
            categories = category_model.get_all_categories()
            health_stats = health_filter_model.get_health_stats()
            
            # Fix the issue with None tags causing an error in the admin dashboard
            total_tags = sum(len(p.get('tags', '').split(',')) for p in products if p.get('tags') is not None)
            
            return render_template('admin/admin.html',
                                 total_products=len(products),
                                 total_categories=len(categories),
                                 total_filters=len(health_stats),
                                 total_tags=total_tags,
                                 health_stats=health_stats)
        except Exception as e:
            self.logger.error(f"Error in admin dashboard: {str(e)}")
            flash('Error loading dashboard statistics', 'error')
            return render_template('admin/admin.html',
                                 total_products=0,
                                 total_categories=0,
                                 total_filters=0,
                                 total_tags=0,
                                 health_stats=[])
    
    def admin_login(self):
        """Admin login page"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
                session['admin_logged_in'] = True
                flash('Welcome, Admin!', 'success')
                return redirect(url_for('cart.admin'))
            else:
                flash('Invalid credentials', 'error')
        
        return render_template('admin/login.html')
    
    def admin_logout(self):
        """Admin logout"""
        session.pop('admin_logged_in', None)
        flash('Logged out successfully', 'success')
        return redirect(url_for('cart.admin_login'))
    
    def admin_products(self):
        """Product management page"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            self.logger.info("Attempting to load products page")
            
            # Test database connection
            cursor = self.mysql.connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            self.logger.info("Database connection successful")
            
            product_model = Product(self.mysql)
            category_model = Category(self.mysql)
            
            # Get category filter
            category = request.args.get('category', 'all')
            self.logger.info(f"Loading products for category: {category}")
            
            products = product_model.get_all_products(category)
            self.logger.info(f"Retrieved {len(products)} products")
            
            categories = category_model.get_all_categories()
            self.logger.info(f"Retrieved {len(categories)} categories")
            
            return render_template('admin/products.html',
                                 products=products,
                                 categories=categories,
                                 selected_category=category)
        except Exception as e:
            self.logger.error(f"Error loading products: {str(e)}")
            self.logger.exception("Full traceback:")  # This will log the full traceback
            flash('Error loading products', 'error')
            return redirect(url_for('cart.admin'))
    
    def add_product(self):
        """Add new product"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        if request.method == 'POST':
            try:
                self.logger.info("Attempting to add new product")
                self.logger.info(f"Form data: {request.form}")
                self.logger.info(f"Files: {request.files}")
                
                # Test database connection
                cursor = self.mysql.connection.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
                self.logger.info("Database connection successful")
                
                product_model = Product(self.mysql)
                
                # Validate required fields
                required_fields = ['name', 'category', 'price', 'weight', 'fat', 'sugars', 'sodium']
                for field in required_fields:
                    if not request.form.get(field):
                        self.logger.error(f"Missing required field: {field}")
                        flash(f'Missing required field: {field}', 'error')
                        return redirect(request.url)
                
                # Validate image
                if 'image' not in request.files:
                    self.logger.error("No image file in request")
                    flash('No image file provided', 'error')
                    return redirect(request.url)
                
                file = request.files['image']
                if file.filename == '':
                    self.logger.error("No selected file")
                    flash('No selected file', 'error')
                    return redirect(request.url)
                
                if not product_model.allowed_file(file.filename):
                    self.logger.error(f"Invalid file type: {file.filename}")
                    flash('Invalid file type. Allowed types are: png, jpg, jpeg, gif, webp', 'error')
                    return redirect(request.url)
                
                # Get the absolute path to the app root
                app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.logger.info(f"App root path: {app_root}")
                
                # Add product
                try:
                    product_model.add_product(request.form, file, app_root)
                    self.logger.info("Product added successfully")
                    flash('Product added successfully!', 'success')
                    return redirect(url_for('cart.admin_products'))
                except Exception as e:
                    self.logger.error(f"Error in add_product: {str(e)}")
                    flash(f'Error adding product: {str(e)}', 'error')
                    return redirect(request.url)
                
            except Exception as e:
                self.logger.error(f"Error adding product: {str(e)}")
                self.logger.exception("Full traceback:")
                flash(f'Error adding product: {str(e)}', 'error')
                return redirect(request.url)
        
        try:
            self.logger.info("Loading add product form")
            category_model = Category(self.mysql)
            categories = category_model.get_all_categories()
            self.logger.info(f"Retrieved {len(categories)} categories")
            return render_template('admin/add_product.html', categories=categories)
        except Exception as e:
            self.logger.error(f"Error loading categories: {str(e)}")
            self.logger.exception("Full traceback:")
            flash('Error loading categories', 'error')
            return redirect(url_for('cart.admin_products'))
    
    def edit_product(self, product_id):
        """Edit existing product"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            product_model = Product(self.mysql)
            category_model = Category(self.mysql)
            
            if request.method == 'POST':
                self.logger.info(f"Attempting to update product {product_id}")
                self.logger.info(f"Form data: {request.form}")
                self.logger.info(f"Files: {request.files}")
                
                # Validate required fields
                required_fields = ['name', 'price', 'weight', 'fat', 'sugars', 'sodium']
                for field in required_fields:
                    if not request.form.get(field):
                        self.logger.error(f"Missing required field: {field}")
                        flash(f'Missing required field: {field}', 'error')
                        return redirect(request.url)
                
                # Handle file upload
                file = request.files.get('image')
                if file and file.filename != '':
                    if not product_model.allowed_file(file.filename):
                        self.logger.error(f"Invalid file type: {file.filename}")
                        flash('Invalid file type. Allowed types are: png, jpg, jpeg, gif, webp', 'error')
                        return redirect(request.url)
                
                # Get the absolute path to the app root
                app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.logger.info(f"App root path: {app_root}")
                
                # Update product
                try:
                    product_model.update_product(product_id, request.form, file, app_root)
                    self.logger.info("Product updated successfully")
                    flash('Product updated successfully!', 'success')
                    return redirect(url_for('cart.admin_products'))
                except Exception as e:
                    self.logger.error(f"Error in update_product: {str(e)}")
                    flash(f'Error updating product: {str(e)}', 'error')
                    return redirect(request.url)
            
            # Get product data for edit form
            product = product_model.get_product_by_id(product_id)
            if not product:
                self.logger.error(f"Product {product_id} not found")
                flash('Product not found', 'error')
                return redirect(url_for('cart.admin_products'))
            
            self.logger.info(f"Loading edit form for product {product_id}")
            categories = category_model.get_all_categories()
            return render_template('admin/edit_product.html',
                                 product=product,
                                 categories=categories,
                                 timestamp=datetime.now().timestamp())
        except Exception as e:
            self.logger.error(f"Error editing product: {str(e)}")
            self.logger.exception("Full traceback:")
            flash(f'Error editing product: {str(e)}', 'error')
            return redirect(url_for('cart.admin_products'))
    
    def delete_product(self, product_id):
        """Delete product"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            # Get the absolute path to the app root
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.logger.info(f"App root path: {app_root}")
            
            product_model = Product(self.mysql)
            if product_model.delete_product(product_id, app_root):
                flash('Product deleted successfully!', 'success')
            else:
                flash('Product not found', 'error')
        except Exception as e:
            self.logger.error(f"Error deleting product: {str(e)}")
            flash('Error deleting product', 'error')
        
        return redirect(url_for('cart.admin_products'))
    
    def snacks(self):
        """Snacks category page"""
        try:
            self.logger.info("Attempting to load snacks category")
            product_model = Product(self.mysql)
            
            # Get products
            products = product_model.get_all_products('snacks')
            self.logger.info(f"Retrieved {len(products)} products for snacks category")
            
            # Update image URLs to use cart's static directory
            for product in products:
                if product['image_url'] and not product['image_url'].startswith('/cart/static'):
                    product['image_url'] = f"/cart/static/images/products/snacks/{product['image_url'].split('/')[-1]}"
            
            # Log template rendering attempt
            self.logger.info("Attempting to render snacks.html template")
            return render_template('snacks.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading snacks: {str(e)}")
            self.logger.exception("Full traceback:")
            flash('Error loading snacks', 'error')
            return redirect(url_for('cart.index'))
    
    def breakfast(self):
        """Breakfast cereals category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('breakfast-cereals')
            return render_template('breakfast.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading breakfast products: {str(e)}")
            flash('Error loading breakfast products', 'error')
            return redirect(url_for('cart.index'))
    
    def chocolates(self):
        """Chocolates category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('chocolates')
            return render_template('chocolates.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading chocolates: {str(e)}")
            flash('Error loading chocolates', 'error')
            return redirect(url_for('cart.index'))
    
    def cold_drinks(self):
        """Cold Drinks and Juices category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('beverages')
            return render_template('cold_drinks.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading cold drinks: {str(e)}")
            flash('Error loading cold drinks and juices', 'error')
            return redirect(url_for('cart.index'))
    
    def drinks(self):
        """Beverages category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('beverages')
            return render_template('drinks.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading beverages: {str(e)}")
            flash('Error loading beverages', 'error')
            return redirect(url_for('cart.index'))
    
    def dairy(self):
        """Dairy products category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('dairy')
            return render_template('dairy.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading dairy products: {str(e)}")
            flash('Error loading dairy products', 'error')
            return redirect(url_for('cart.index'))
    
    def instant(self):
        """Instant foods category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('instant-foods')
            return render_template('instant.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading instant foods: {str(e)}")
            flash('Error loading instant foods', 'error')
            return redirect(url_for('cart.index'))
    
    def groceries(self):
        """Groceries category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('groceries')
            return render_template('groceries.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading groceries: {str(e)}")
            flash('Error loading groceries', 'error')
            return redirect(url_for('cart.index'))
    
    def supplements(self):
        """Food supplements category page"""
        try:
            category_model = Category(self.mysql)
            products = category_model.get_products_by_category('food-supplements')
            return render_template('supplements.html', products=products)
        except Exception as e:
            self.logger.error(f"Error loading supplements: {str(e)}")
            flash('Error loading supplements', 'error')
            return redirect(url_for('cart.index'))
    
    def admin_categories(self):
        """Category management page"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            category_model = Category(self.mysql)
            categories = category_model.get_all_categories()
            return render_template('admin/categories.html', categories=categories)
        except Exception as e:
            self.logger.error(f"Error loading categories: {str(e)}")
            flash('Error loading categories', 'error')
            return redirect(url_for('cart.admin'))
    
    def edit_category(self, category_name):
        """Edit category page"""
        if 'admin_logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('cart.admin_login'))
            
        try:
            category_model = Category(self.mysql)
            
            if request.method == 'POST':
                new_name = request.form.get('name')
                if not new_name:
                    flash('Category name is required', 'error')
                    return redirect(request.url)
                
                try:
                    category_model.edit_category(category_name, new_name)
                    flash('Category updated successfully!', 'success')
                    return redirect(url_for('cart.admin_categories'))
                except ValueError as e:
                    flash(str(e), 'error')
                    return redirect(request.url)
            
            return render_template('admin/edit_category.html', category_name=category_name)
        except Exception as e:
            self.logger.error(f"Error editing category: {str(e)}")
            flash('Error editing category', 'error')
            return redirect(url_for('cart.admin_categories'))

def init_app(app):
    """Initialize the cart blueprint with the main app"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Configure MySQL
    app.config['MYSQL_HOST'] = Config.MYSQL_HOST
    app.config['MYSQL_USER'] = Config.MYSQL_USER
    app.config['MYSQL_PASSWORD'] = Config.MYSQL_PASSWORD
    app.config['MYSQL_DB'] = Config.MYSQL_DB
    
    # Create cart blueprint instance
    cart = CartBlueprint()
    
    # Register blueprint and initialize MySQL
    app.register_blueprint(cart.blueprint)
    cart.mysql.init_app(app)
    
    # Test MySQL connection
    try:
        with app.app_context():
            cursor = cart.mysql.connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            logger.info("MySQL connection successful")
    except Exception as e:
        logger.error(f"MySQL connection failed: {str(e)}")
        logger.exception("Full traceback:")
    
    # Create necessary directories for product images
    categories = ['snacks', 'breakfast', 'chocolates', 'cold-drinks', 'dairy', 'instant', 'groceries', 'supplements']
    for category in categories:
        category_path = os.path.join(app.root_path, Config.UPLOAD_FOLDER, category)
        os.makedirs(category_path, exist_ok=True)
        logger.info(f"Created directory: {category_path}")
    
    # Create no-image placeholder
    no_image_path = os.path.join(app.root_path, Config.UPLOAD_FOLDER, 'no-image.png')
    if not os.path.exists(no_image_path):
        try:
            import shutil
            import requests
            response = requests.get('https://raw.githubusercontent.com/common-resources/placeholder-images/main/no-image-available.png', stream=True)
            if response.status_code == 200:
                with open(no_image_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                logger.info(f"Created no-image placeholder at: {no_image_path}")
        except Exception as e:
            logger.error(f"Failed to create no-image placeholder: {str(e)}")
    
    # Set secret key
    app.secret_key = Config.SECRET_KEY if hasattr(Config, 'SECRET_KEY') else 'your-secret-key-here'

# Create Flask app instance
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Add root route to redirect to cart blueprint
@app.route('/')
def root():
    return redirect(url_for('cart.index'))

# Initialize the cart blueprint
init_app(app)

if __name__ == '__main__':
    app.run(debug=True)