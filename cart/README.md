# Cart Module

This is a Flask blueprint module for managing a product catalog with health-based filtering.

## Features

- Product management (CRUD operations)
- Category-based organization
- Health-based filtering
- Image upload support
- Admin interface
- Tag-based categorization

## Database Structure

The module uses the following tables:
- users
- health_data
- categories
- products
- health_filters
- product_health_restrictions
- product_tags

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up the database:
```bash
mysql -u root -p < setup_database.sql
```

3. Configure the module:
   - Update `config.py` with your database credentials and other settings
   - Make sure the upload directory exists and is writable

4. Integration with main Flask app:
```python
from flask import Flask
from cart import init_app as init_cart

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-here'
    
    # Initialize the cart blueprint
    init_cart(app)
    
    return app
```

## Usage

The module is accessible at `/cart/` with the following main routes:

- `/cart/` - Main catalog page
- `/cart/admin` - Admin dashboard
- `/cart/admin/products` - Product management
- `/cart/snacks` - Snacks category
- `/cart/breakfast` - Breakfast cereals category
- `/cart/chocolates` - Chocolates category
- `/cart/drinks` - Beverages category
- `/cart/dairy` - Dairy products category
- `/cart/instant` - Instant foods category
- `/cart/groceries` - Groceries category
- `/cart/supplements` - Food supplements category

## Project Structure

```
cart/
├── __init__.py
├── app.py
├── config.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── product.py
│   ├── category.py
│   └── health_filter.py
├── templates/
│   ├── admin/
│   │   ├── admin.html
│   │   ├── login.html
│   │   ├── products.html
│   │   ├── add_product.html
│   │   └── edit_product.html
│   ├── categories.html
│   ├── product_base.html
│   └── category-specific templates
├── static/
│   ├── images/
│   │   └── products/
│   ├── styles.css
│   ├── product-page.css
│   └── products.js
└── requirements.txt
```

## Dependencies

- Flask 3.0.2
- requests 2.31.0
- flask-mysqldb 1.0.1

## Security Notes

1. Admin credentials are currently hardcoded in config.py. In production:
   - Move credentials to environment variables
   - Use proper password hashing
   - Implement proper session management

2. File uploads:
   - Validate file types
   - Implement file size limits
   - Use secure filenames
   - Store files outside web root

3. Database:
   - Use parameterized queries
   - Implement proper connection pooling
   - Use environment variables for credentials 