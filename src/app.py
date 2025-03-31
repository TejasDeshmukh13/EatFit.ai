import os
from flask import Flask, g, redirect, url_for, request, jsonify, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import logging

# Import config and database
from config.database import DB_CONFIG
from database.db import init_app

# Import cart blueprint
from cart import CartBlueprint

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# App configuration
app.secret_key = os.urandom(24)

# MySQL configurations from config module
app.config.update(DB_CONFIG)

# Configuration for file upload
UPLOAD_FOLDER = os.path.join('src', 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join('src', 'static', 'images'), exist_ok=True)

# Initialize extensions
mysql = MySQL(app)
bcrypt = Bcrypt(app)

# Initialize database
init_app(app)

@app.before_request
def before_request():
    """Set up extensions for request."""
    if request.path.startswith('/static/'):
        return
        
    g.mysql = mysql
    g.app = app
    g.bcrypt = bcrypt

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.product_routes import product_bp
from routes.diet_routes import diet_bp

# Initialize and register cart blueprint
cart_blueprint = CartBlueprint()
app.register_blueprint(cart_blueprint.blueprint)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(product_bp, url_prefix='/product')
app.register_blueprint(diet_bp, url_prefix='/diet')

# Default route
@app.route('/')
def index():
    return redirect(url_for('product.landing_page'))

@app.route('/api/diet/recommend', methods=['POST'])
def get_diet_recommendation():
    try:
        data = request.get_json()
        age = data.get('age')
        weight = data.get('weight')
        height = data.get('height')
        disease = data.get('disease')
        
        if not all([age, weight, height]):
            return jsonify({
                'error': 'Missing required fields. Please provide age, weight, and height.'
            }), 400
            
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal( # type: ignore
            age=float(age),
            weight=float(weight),
            height_ft=float(height),
            disease=disease
        )
        
        return jsonify({
            'bmi': round(bmi, 2),
            'bmi_category': bmi_category,
            'recommendations': {
                'breakfast': breakfast,
                'lunch': lunch,
                'dinner': dinner
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Recommendation failed: {str(e)}'
        }), 500

def create_app(config=None):
    app = Flask(__name__)
    
    # Configure app
    if config:
        app.config.update(config)
    else:
        app.config.from_object('config.DefaultConfig')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Create static/images folder
    os.makedirs(os.path.join(app.static_folder, 'images'), exist_ok=True)
    
    # Generate score images if they don't exist
    generate_score_images(app.static_folder)
    
    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.product_routes import product_bp
    # from routes.main_routes import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    # app.register_blueprint(main_bp)
    
    # Set app in g before each request
    @app.before_request
    def set_app():
        g.app = app
    
    return app

# Function to generate score images
def generate_score_images(static_folder):
    """Generate score images for Nutri-Score"""
    import base64
    
    images_folder = os.path.join(static_folder, 'images')
    
    # Define the Nutri-Score SVGs
    nutri_colors = {
        'a': '#0a8e45',
        'b': '#7ac547',
        'c': '#ffc734',
        'd': '#ff7d24',
        'e': '#e63e11'
    }
    
    # Create icon placeholder SVG
    def create_nutri_svg(score, color):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">
            <rect width="120" height="40" fill="{color}" rx="4"/>
            <text x="12" y="26" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="white">A</text>
            <text x="36" y="26" font-family="Arial, sans-serif" font-size="18" fill="white">B</text>
            <text x="60" y="26" font-family="Arial, sans-serif" font-size="18" fill="white">C</text>
            <text x="84" y="26" font-family="Arial, sans-serif" font-size="18" fill="white">D</text>
            <text x="108" y="26" font-family="Arial, sans-serif" font-size="18" fill="white">E</text>
        </svg>'''
        return svg
    
    # Generate placeholder SVG for each score
    for score, color in nutri_colors.items():
        file_path = os.path.join(images_folder, f'nutriscore-{score}.png')
        if not os.path.exists(file_path):
            print(f"Created placeholder for nutriscore-{score}.png")
            # Just create an empty file as a placeholder
            with open(file_path, 'w') as f:
                f.write('')

if __name__ == '__main__':
    app.run(debug=True, port=5001) 