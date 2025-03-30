from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.utils import secure_filename
import os
import io
from utils.common import allowed_file
from utils.image_processing import OCR_CONFIGS, extract_text
from utils.nutrition import (
    parse_nutrition, process_with_config, calculate_nutri_score, 
    fetch_by_barcode, get_alternatives_by_category,
    get_nova_score, get_product_match_percentage
)
from utils.allergies import map_allergens_to_ingredients
from utils.conclusion import check_product_safety
from models.food_analysis import analyze_product_with_off, ProductAnalysis
import logging
import json
import requests

# Set up logging
logger = logging.getLogger(__name__)

product_bp = Blueprint('product', __name__)

# REST API for food analysis
@product_bp.route('/api/food/analyze', methods=['POST'])
def analyze_food_api():
    """
    API endpoint to analyze a food product based on its barcode.
    
    Expected JSON payload:
    {
        "barcode": "3017620425035"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'barcode' not in data:
            return jsonify({
                'error': 'Missing barcode. Please provide a valid barcode.',
                'text_result': 'Product Analysis Results\n\nNo barcode provided.'
            }), 400
        
        barcode = data['barcode']
        
        # Analyze product using the food_analysis module
        analysis = analyze_product_with_off(barcode)
        
        if not analysis:
            return jsonify({
                'error': 'Product not found or no data available.',
                'text_result': 'Product Analysis Results\n\nNo data available for this barcode.'
            }), 404
        
        # Convert analysis to dictionary
        try:
            analysis_dict = analysis.to_dict()
        except Exception as e:
            print(f"Error converting analysis to dictionary: {str(e)}")
            return jsonify({
                'error': f'Error processing analysis: {str(e)}',
                'text_result': 'Product Analysis Results\n\nError processing product analysis.'
            }), 500
        
        # Ensure we have required nested dictionaries
        if 'processing' not in analysis_dict:
            analysis_dict['processing'] = {}
        if 'additives' not in analysis_dict:
            analysis_dict['additives'] = []
        if 'ingredients' not in analysis_dict:
            analysis_dict['ingredients'] = {}
        
        # Generate text result
        text_result = f"Product Analysis Results\n\n"
        
        if analysis_dict.get('product_name'):
            text_result += f"Product: {analysis_dict.get('product_name')}\n\n"
            
        text_result += "Food Processing\n"
        if analysis_dict['processing'].get('nova_group'):
            text_result += f"NOVA Group: {analysis_dict['processing'].get('nova_group')}\n"
        else:
            text_result += "Processing information not available\n"
            
        text_result += "\nAdditives\n"
        if analysis_dict['additives']:
            for additive in analysis_dict['additives']:
                text_result += f"{additive.get('code', 'Unknown')} - {additive.get('name', 'Unknown')}\n"
        else:
            text_result += "No additives information available\n"
            
        text_result += "\nIngredients Analysis\n"
        
        # Palm oil
        if analysis_dict['ingredients'].get('palm_oil'):
            text_result += "🌴 Contains palm oil\n"
            
        # Vegan status
        if not analysis_dict['ingredients'].get('vegan', True):
            text_result += "🥩 Non-vegan\n"
            
        # Allergens
        allergens = analysis_dict['ingredients'].get('allergens', [])
        if allergens and isinstance(allergens, list):
            text_result += f"⚠️ Contains allergens: {', '.join(allergens)}\n"
            
        # Traces
        traces = analysis_dict['ingredients'].get('traces', [])
        if traces and isinstance(traces, list):
            text_result += f"⚠️ May contain traces of: {', '.join(traces)}\n"
        
        return jsonify({
            'text_result': text_result,
            'data': analysis_dict
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print detailed stack trace
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'text_result': 'Product Analysis Results\n\nError occurred while analyzing the product.'
        }), 500

# Routes
@product_bp.route('/landing_page')
def landing_page():
    return render_template('landing_page.html')

@product_bp.route("/upload_file", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        # Get barcode if provided
        barcode = request.form.get('barcode', '').strip()
        has_file = 'file' in request.files and request.files['file'].filename
        
        # Check if neither file nor barcode is provided
        if not has_file and not barcode:
            flash("Please provide either an image or a barcode number", "error")
            return render_template("upload.html")

        # If barcode is provided but no file, fetch data directly from API
        if barcode and not has_file:
            try:
                # Process with food analysis module
                analysis = analyze_product_with_off(barcode)
                
                if not analysis:
                    flash("Product not found or no data available", "error")
                    return render_template("upload.html")
                
                # Store analysis in session
                analysis_dict = analysis.to_dict()
                session['nutrition'] = analysis_dict
                session['product_name'] = analysis_dict.get('product_name', 'Unknown Product')
                session['brand'] = analysis_dict.get('brand', 'Unknown Brand')
                session['barcode'] = barcode
                session['from_barcode_only'] = True
                
                flash(f"Found product: {session['product_name']} by {session['brand']}", "success")
                return redirect(url_for('product.product_details'))
                
            except Exception as e:
                flash(f"Error processing barcode: {str(e)}", "error")
                return render_template("upload.html")
        
        # Process file upload
        if has_file:
            file = request.files["file"]
            
            if not allowed_file(file.filename):
                flash("File type not allowed. Please upload an image (JPG, PNG, etc.)", "error")
                return render_template("upload.html")

            try:
                # Save the uploaded file
                filename = secure_filename(file.filename)
                app_config = g.app.config
                upload_path = os.path.join(app_config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                
                # Store file information in session
                session['file_path'] = upload_path
                session['filename'] = filename
                session['current_config_idx'] = 0
                session['from_barcode_only'] = False
                
                # Store barcode in session if provided along with image
                if barcode:
                    session['barcode'] = barcode
                else:
                    session.pop('barcode', None)
                
                # Process the image with OCR
                nutrition_data = process_with_config(upload_path, 0)
                
                if isinstance(nutrition_data, dict) and not nutrition_data.get('error'):
                    # If we have a barcode, try to get additional data
                    if barcode:
                        analysis = analyze_product_with_off(barcode)
                        if analysis:
                            analysis_dict = analysis.to_dict()
                            # Merge OCR data with API data
                            nutrition_data.update(analysis_dict)
                            session['product_name'] = analysis_dict.get('product_name')
                            session['brand'] = analysis_dict.get('brand')
                            flash(f"Found product: {analysis_dict.get('product_name')}", "success")
                    
                    session['nutrition'] = nutrition_data
                    flash("Image processed successfully! Please verify the extracted information.", "success")
                else:
                    session['nutrition'] = {}
                    error_msg = nutrition_data.get('error', 'Failed to extract nutrition information')
                    flash(f"OCR processing issue: {error_msg}. Please enter the values manually.", "warning")
                    
                return redirect(url_for('product.verify_extraction'))
                
            except Exception as e:
                flash(f"Error processing upload: {str(e)}", "error")
                return render_template("upload.html")

    return render_template("upload.html")

@product_bp.route("/verify", methods=["GET", "POST"])
def verify_extraction():
    if 'file_path' not in session or 'filename' not in session:
        flash("No image uploaded", "error")
        return redirect(url_for('product.upload_file'))
    
    if request.method == 'POST':
        if request.form.get('user_response') == 'accept':
            # Create a clean nutrition dictionary from form data
            nutrition = {}
            fields = [
                'energy_kcal', 'fat', 'saturated_fat',
                'carbohydrates', 'sugars', 'fiber',
                'protein', 'salt'
            ]
            
            # Check if any fields have valid values
            has_valid_data = False
            
            for field in fields:
                value = request.form.get(field, '').strip()
                if value:
                    try:
                        # Convert any comma to period for proper float parsing
                        value = value.replace(',', '.')
                        float_value = float(value)
                        
                        if float_value >= 0:  # Ensure no negative values
                            nutrition[field] = float_value
                            has_valid_data = True
                        else:
                            flash(f'Negative value for {field.replace("_", " ")} is not allowed', 'error')
                            return redirect(url_for('product.verify_extraction'))
                    except ValueError:
                        flash(f'Invalid value for {field.replace("_", " ")}: {value}', 'error')
                        return redirect(url_for('product.verify_extraction'))
            
            if not has_valid_data:
                flash('Please enter at least some nutrition values', 'error')
                return redirect(url_for('product.verify_extraction'))
            
            # Add product information from API if available
            if 'product_name' in session:
                nutrition['product_name'] = session['product_name']
            if 'brand' in session:
                nutrition['brand'] = session['brand']
            
            # Store the nutrition data in session
            session['nutrition'] = nutrition
            
            # Calculate nutri-score
            try:
                session['nutri_grade'] = calculate_nutri_score(nutrition)
                flash(f"Nutri-Score calculated: {session['nutri_grade']}", "success")
            except Exception as e:
                print(f"Error calculating nutri-score: {str(e)}")
                session['nutri_grade'] = 'C'  # Default if calculation fails
                flash("Could not calculate accurate Nutri-Score. Using default grade C.", "warning")
                
            return redirect(url_for('product.product_details'))
        else:
            # Try another OCR configuration
            current_idx = session.get('current_config_idx', 0)
            new_idx = (current_idx + 1) % len(OCR_CONFIGS)
            
            try:
                session['current_config_idx'] = new_idx
                barcode = session.get('barcode', None)
                nutrition_data = process_with_config(session['file_path'], new_idx, barcode)
                
                # Make sure the result is a dictionary
                if isinstance(nutrition_data, dict) and not nutrition_data.get('error'):
                    session['nutrition'] = nutrition_data
                    
                    # If product data from API is available, preserve it
                    if barcode and 'product_name' in nutrition_data:
                        session['product_name'] = nutrition_data.get('product_name')
                        session['brand'] = nutrition_data.get('brand', 'Unknown Brand')
                        
                    flash(f"Tried OCR configuration #{new_idx+1}. Please verify the extracted values.", "info")
                else:
                    error_msg = nutrition_data.get('error', 'No nutrition data extracted')
                    flash(f"OCR configuration #{new_idx+1} failed: {error_msg}. Please try another or enter values manually.", "warning")
                    # Keep previous nutrition data if available
                    if 'nutrition' not in session:
                        session['nutrition'] = {}
            except Exception as e:
                flash(f"Error processing image: {str(e)}", "error")
                if 'nutrition' not in session:
                    session['nutrition'] = {}
                
            return redirect(url_for('product.verify_extraction'))
    
    # Get session values with defaults
    nutrition = session.get('nutrition', {})
    config_number = session.get('current_config_idx', 0) + 1
    
    # Check if product info from barcode is available
    product_info = ""
    if 'product_name' in session and 'brand' in session:
        product_info = f"{session['product_name']} by {session['brand']}"
    
    # Ensure filename exists and is valid
    filename = session.get('filename', '')
    
    if not filename:
        flash("Image not found", "error")
        return redirect(url_for('product.upload_file'))
    
    return render_template(
        "verify.html",
        image=filename,
        nutrition=nutrition,
        config_number=config_number,
        product_info=product_info
    )

def translate_ingredient(name):
    translations = {
        'sucre': 'sugar',
        'huile de palme': 'palm oil',
        'NOISETTES': 'hazelnuts',
        'LAIT écrémé en poudre': 'skimmed milk powder',
        'cacao maigre': 'low-fat cocoa',
        'émulsifiants': 'emulsifiers',
        'vanilline': 'vanillin',
        'lécithines': 'lecithins',
        'lécithines de SOJA': 'SOY lecithins'
    }
    return translations.get(name.lower(), name)

@product_bp.route("/product_details")
def product_details():
    """Display detailed product analysis including nutrition, processing, and ingredients"""
    if 'nutrition' not in session:
        logger.warning("No nutrition data in session")
        flash("No product data available", "error")
        return redirect(url_for('product.upload_file'))
        
    try:
        # Get the analysis data
        nutrition_data = session.get('nutrition', {})
        logger.info(f"Initial nutrition data keys: {nutrition_data.keys()}")
        
        # If we have a barcode, ensure we have the latest analysis
        if 'barcode' in session and session.get('from_barcode_only', False):
            barcode = session['barcode']
            logger.info(f"Fetching latest analysis for barcode: {barcode}")
            
            # Fetch fresh data from API
            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    product = data.get('product', {})
                    
                    # Update nutrition data with API data
                    if 'nutriments' in product:
                        nutrition_data.update(product['nutriments'])
                    
                    # Get ingredients list
                    if 'ingredients_text' in product:
                        nutrition_data['ingredients_text'] = product['ingredients_text']
                    
                    # Get detailed ingredients
                    if 'ingredients' in product:
                        nutrition_data['ingredients_detailed'] = []
                        for ingredient in product['ingredients']:
                            if isinstance(ingredient, dict):
                                ingredient_info = {
                                    'text': ingredient.get('text', ''),
                                    'name': ingredient.get('id', '').split(':')[-1].replace('-', ' ').title()
                                }
                                nutrition_data['ingredients_detailed'].append(ingredient_info)
                        
                    # Get allergens and traces
                    if 'allergens_tags' in product:
                        nutrition_data['allergens_tags'] = [
                            tag.split(':')[-1].replace('-', ' ').title() 
                            for tag in product['allergens_tags']
                        ]
                    if 'traces_tags' in product:
                        nutrition_data['traces_tags'] = [
                            tag.split(':')[-1].replace('-', ' ').title() 
                            for tag in product['traces_tags']
                        ]
                        
                    session['nutrition'] = nutrition_data
        
        # Get ingredients for allergy analysis
        ingredients = []
        
        # Try to get ingredients from detailed list first
        if 'ingredients_detailed' in nutrition_data:
            for ingredient in nutrition_data['ingredients_detailed']:
                if isinstance(ingredient, dict):
                    name = ingredient.get('text', '') or ingredient.get('name', '')
                    if name:
                        ingredients.append(name)
        
        # Fallback to ingredients text if no detailed list
        elif 'ingredients_text' in nutrition_data:
            ingredients = [i.strip() for i in nutrition_data['ingredients_text'].split(',')]
        
        # Get allergens from product data
        allergens = nutrition_data.get('allergens_tags', [])
        if allergens:
            ingredients.extend(allergens)
            logger.info(f"Found {len(allergens)} direct allergens: {allergens}")
        
        # Get traces from product data
        traces = nutrition_data.get('traces_tags', [])
        if traces:
            ingredients.extend(traces)
            logger.info(f"Found {len(traces)} traces: {traces}")
        
        # Remove duplicates and empty strings
        ingredients = list(set(filter(None, ingredients)))
        logger.info(f"Total unique ingredients to analyze: {len(ingredients)}")
        
        # Get allergy information
        allergies = []
        if ingredients:
            try:
                allergies = map_allergens_to_ingredients(ingredients)
                logger.info(f"Found {len(allergies)} potential allergens")
            except Exception as e:
                logger.error(f"Error in allergy analysis: {str(e)}")
                flash("Error analyzing allergens", "warning")
        
        # Get user login status and health data
        is_logged_in = 'user_id' in session
        user_health = None
        
        if is_logged_in:
            try:
                # Fetch user's health data from database
                mysql = g.mysql
                cur = mysql.connection.cursor()
                cur.execute("""
                    SELECT height, weight, age, bmi, diabetes, bp, cholesterol
                    FROM health_data 
                    WHERE user_id = %s
                    ORDER BY id DESC LIMIT 1
                """, (session['user_id'],))
                
                health_data = cur.fetchone()
                cur.close()
                
                if health_data:
                    user_health = {
                        'height': health_data[0],
                        'weight': health_data[1],
                        'age': health_data[2],
                        'bmi': health_data[3],
                        'diabetes': health_data[4] != 'none',
                        'bp': health_data[5] == 'high',
                        'cholesterol': health_data[6] == 'high'
                    }
                    logger.info("Loaded user health data for safety analysis")
            except Exception as e:
                logger.error(f"Error fetching health data: {str(e)}")
        
        # Get health analysis
        safety_review = check_product_safety(nutrition_data, user_health) if user_health else {
            "conclusion": "Log in and update your health profile for personalized recommendations.",
            "warnings": [],
            "safe_nutrients": []
        }
        
        # Get NOVA score and Nutri-Score
        nova_score = get_nova_score(nutrition_data)
        score = calculate_nutri_score(nutrition_data)
        
        return render_template(
            'product_details.html',
            nutrition=nutrition_data,
            allergies=allergies,
            safety_review=safety_review,
            is_logged_in=is_logged_in,
            nova_score=nova_score,
            score=score,
            image=session.get('image', 'no-image.png'),
            product_name=session.get('product_name', 'Unknown Product'),
            brand=session.get('brand', 'Unknown Brand')
        )
        
    except Exception as e:
        logger.error(f"Error displaying product details: {str(e)}")
        flash(f"Error displaying product details: {str(e)}", "error")
        return redirect(url_for('product.upload_file'))

@product_bp.route('/alternative_products')
def alternative_products():
    """Find healthier alternative products based on current product analysis"""
    try:
        # Check if we have product data
        if 'nutrition' not in session:
            flash("Please scan a product first to find alternatives", "warning")
            return redirect(url_for('product.upload_file'))
        
        # Get current product details
        nutrition_data = session.get('nutrition', {})
        if not isinstance(nutrition_data, dict):
            nutrition_data = {}
        
        # Get the current product's nutriscore grade
        current_score = None
        if isinstance(nutrition_data, dict):
            current_score = nutrition_data.get('nutriscore_grade', 'C')
        
        alternatives = []
        barcode = session.get('barcode')
        
        if barcode:
            try:
                # Get alternatives from the same category with better scores
                category_alternatives = get_alternatives_by_category(barcode, current_score)
                
                if category_alternatives and isinstance(category_alternatives, list):
                    alternatives.extend(category_alternatives)
            except Exception as e:
                logger.error(f"Error getting category alternatives: {str(e)}")
        
        # If no alternatives found or error occurred, provide healthy generic alternatives
        if not alternatives:
            alternatives = [
                {
                    'product_name': 'Fresh Fruit Bowl',
                    'image_url': url_for('static', filename='images/diet.jpg'),
                    'nutriscore_grade': 'A',
                    'nova_group': 1,
                    'reason': 'Natural • Unprocessed • Rich in vitamins'
                },
                {
                    'product_name': 'Greek Yogurt with Honey',
                    'image_url': url_for('static', filename='images/F1.png'),
                    'nutriscore_grade': 'A',
                    'nova_group': 1,
                    'reason': 'High protein • Probiotic • Natural sweetness'
                },
                {
                    'product_name': 'Whole Grain Toast with Avocado',
                    'image_url': url_for('static', filename='images/pack_fd_re.jpg'),
                    'nutriscore_grade': 'B',
                    'nova_group': 2,
                    'reason': 'Healthy fats • High fiber • Complex carbs'
                }
            ]
        
        return render_template(
            "alternative_products.html", 
            alternatives=alternatives,
            current_product=session.get('product_name', 'Current Product')
        )
        
    except Exception as e:
        logger.error(f"Error finding alternatives: {str(e)}")
        flash("An error occurred while finding alternatives. Please try again.", "error")
        return redirect(url_for('product.product_details'))

@product_bp.route('/demo_product/<demo_id>')
def demo_product(demo_id):
    """Show demo products with predefined analysis"""
    # Define demo product barcodes
    demo_barcodes = {
        'chocolate': '3017620422003',  # Nutella
        'cereal': '5000127169389',    # Special K
        'yogurt': '021908449004'      # Greek Yogurt
    }
    
    try:
        # Get the demo barcode or default to chocolate
        barcode = demo_barcodes.get(demo_id, demo_barcodes['chocolate'])
        
        # Analyze the demo product
        analysis = analyze_product_with_off(barcode)
        
        if not analysis:
            # If Open Food Facts API fails, provide fallback data
            flash("Using fallback demo product data", "warning")
            fallback_data = {
                'product_name': f'Demo {demo_id.title()} Product',
                'brand': 'Demo Brand',
                'nutrition': {'nutriscore_grade': 'C'},
                'processing': {'nova_group': 3},
                'ingredients': {
                    'palm_oil': False,
                    'vegan': True,
                    'allergens': [],
                    'traces': []
                },
                'additives': []
            }
            session['nutrition'] = fallback_data
            session['product_name'] = fallback_data['product_name']
            session['brand'] = fallback_data['brand']
            session['barcode'] = barcode
            session['from_barcode_only'] = True
            
            flash(f"Demo product loaded: {session['product_name']}", "success")
            return redirect(url_for('product.product_details'))
        
        # Convert analysis to dictionary and verify it's valid
        try:
            analysis_dict = analysis.to_dict()
            
            # Ensure we have required nested dictionaries
            if 'nutrition' not in analysis_dict:
                analysis_dict['nutrition'] = {'nutriscore_grade': 'C'}
            if 'processing' not in analysis_dict:
                analysis_dict['processing'] = {'nova_group': 'Unknown'}
            if 'ingredients' not in analysis_dict:
                analysis_dict['ingredients'] = {}
                
            # Store analysis in session
            session['nutrition'] = analysis_dict
            session['product_name'] = analysis_dict.get('product_name', f'Demo {demo_id.title()} Product')
            session['brand'] = analysis_dict.get('brand', 'Demo Brand')
            session['barcode'] = barcode
            session['from_barcode_only'] = True
            
            flash(f"Demo product loaded: {session['product_name']}", "success")
            
            # Redirect to product details
            return redirect(url_for('product.product_details'))
            
        except Exception as e:
            print(f"Error processing demo product analysis: {str(e)}")
            flash("Error processing demo product data", "error")
            return redirect(url_for('product.upload_file'))
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print detailed stack trace
        flash(f"Error loading demo product: {str(e)}", "error")
        return redirect(url_for('product.upload_file'))

@product_bp.route('/nutrition')
def nutrition_landing():
    return render_template('nutrition_landing.html')

@product_bp.route('/barcode_lookup')
def barcode_lookup():
    return render_template('barcode_lookup.html') 

def get_db_connection():
    mysql = g.mysql
    return mysql.connection.cursor()

def get_meal_alternatives(meal_type, user_profile):
    """
    Generate alternative meal options for the specified meal type
    In a real app, this would use a food database or ML model
    """
    # Define alternative meals for each type
    alternatives = {
        'breakfast': [
            {
                'name': 'Protein-Packed Breakfast',
                'items': [
                    {'name': 'Scrambled eggs with spinach', 'quantity': '3 eggs'},
                    {'name': 'Whole grain toast', 'quantity': '1 slice'},
                    {'name': 'Avocado', 'quantity': '1/4'},
                    {'name': 'Black coffee', 'quantity': None}
                ],
                'calories': 400
            },
            {
                'name': 'Smoothie Bowl',
                'items': [
                    {'name': 'Banana smoothie bowl', 'quantity': '1 bowl'},
                    {'name': 'Mixed berries', 'quantity': '1/2 cup'},
                    {'name': 'Granola', 'quantity': '1/4 cup'},
                    {'name': 'Chia seeds', 'quantity': '1 tbsp'}
                ],
                'calories': 380
            },
            {
                'name': 'Traditional Indian',
                'items': [
                    {'name': 'Vegetable poha', 'quantity': '1 cup'},
                    {'name': 'Roasted peanuts', 'quantity': '1 tbsp'},
                    {'name': 'Mint chutney', 'quantity': '2 tbsp'},
                    {'name': 'Masala chai', 'quantity': '1 cup'}
                ],
                'calories': 320
            }
        ],
        'lunch': [
            {
                'name': 'Mediterranean Bowl',
                'items': [
                    {'name': 'Falafel', 'quantity': '4 pieces'},
                    {'name': 'Tabbouleh salad', 'quantity': '1/2 cup'},
                    {'name': 'Hummus', 'quantity': '2 tbsp'},
                    {'name': 'Whole wheat pita', 'quantity': '1/2 piece'}
                ],
                'calories': 520
            },
            {
                'name': 'Asian Fusion',
                'items': [
                    {'name': 'Tofu stir-fry', 'quantity': '1 cup'},
                    {'name': 'Brown rice', 'quantity': '1/2 cup'},
                    {'name': 'Edamame', 'quantity': '1/4 cup'},
                    {'name': 'Miso soup', 'quantity': '1 cup'}
                ],
                'calories': 480
            },
            {
                'name': 'Indian Thali',
                'items': [
                    {'name': 'Lentil dal', 'quantity': '1/2 cup'},
                    {'name': 'Vegetable curry', 'quantity': '1/2 cup'},
                    {'name': 'Brown rice', 'quantity': '1/3 cup'},
                    {'name': 'Cucumber raita', 'quantity': '1/4 cup'}
                ],
                'calories': 550
            }
        ],
        'dinner': [
            {
                'name': 'Italian Night',
                'items': [
                    {'name': 'Zucchini pasta', 'quantity': '1 cup'},
                    {'name': 'Turkey meatballs', 'quantity': '3 pieces'},
                    {'name': 'Tomato sauce', 'quantity': '1/4 cup'},
                    {'name': 'Side salad with vinaigrette', 'quantity': '1 cup'}
                ],
                'calories': 480
            },
            {
                'name': 'Mexican Bowl',
                'items': [
                    {'name': 'Black bean and corn bowl', 'quantity': '1 cup'},
                    {'name': 'Grilled chicken', 'quantity': '3 oz'},
                    {'name': 'Guacamole', 'quantity': '2 tbsp'},
                    {'name': 'Salsa', 'quantity': '2 tbsp'}
                ],
                'calories': 520
            },
            {
                'name': 'Indian Dinner',
                'items': [
                    {'name': 'Paneer tikka', 'quantity': '4 pieces'},
                    {'name': 'Roti', 'quantity': '1 small'},
                    {'name': 'Palak (spinach) curry', 'quantity': '1/2 cup'},
                    {'name': 'Cucumber salad', 'quantity': '1/2 cup'}
                ],
                'calories': 490
            }
        ]
    }
    
    # Filter alternatives based on user profile
    filtered_alternatives = alternatives.get(meal_type, [])
    
    # Apply dietary restrictions
    diet_type = user_profile.get('diet_type')
    if diet_type == 'vegetarian':
        filtered_alternatives = [alt for alt in filtered_alternatives if not any(
            'chicken' in item['name'].lower() or 
            'turkey' in item['name'].lower() or
            'beef' in item['name'].lower() or
            'fish' in item['name'].lower() or
            'salmon' in item['name'].lower()
            for item in alt['items']
        )]
    
    return filtered_alternatives 