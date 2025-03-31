from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.utils import secure_filename
import os
import io
from utils.common import allowed_file
from utils.image_processing import OCR_CONFIGS, extract_text
from utils.nutrition import (
    parse_nutrition, process_with_config, calculate_nutri_score,
    get_alternatives_by_category, merge_nutrition_data, get_nova_score
)
from utils.allergies import map_allergens_to_ingredients
from utils.conclusion import check_product_safety
from models.food_analysis import get_product_from_off, analyze_product_with_off, ProductAnalysis
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
        if 'barcode' in session:
            barcode = session['barcode']
            logger.info(f"Getting latest data for barcode: {barcode}")
            
            # Get fresh data directly from OpenFoodFacts
            try:
                product = get_product_from_off(barcode)
                
                if product:
                    logger.info(f"Got fresh data from API for barcode {barcode}")
                    
                    # Update nutrition data with the latest API data
                    # Update basic product info
                    nutrition_data['product_name'] = product.get('product_name', 'Unknown Product')
                    nutrition_data['brand'] = product.get('brands', 'Unknown Brand')
                    nutrition_data['image_url'] = product.get('image_url')
                    
                    # Update nutriments from ocr
                    if 'nutriments' in product:
                        for key, value in product['nutriments'].items():
                            nutrition_data[key] = value
                    
                    # Copy all API data fields that should be used in the template
                    for key in [
                        'ingredients_text', 
                        'additives_tags', 
                        'ingredients_analysis_tags',
                        'nova_group', 
                        'nova_score', 
                        'nutriscore_grade', 
                        'allergens_tags', 
                        'traces_tags', 
                        'ingredients', 
                        'is_vegan'
                    ]:
                        if key in product:
                            nutrition_data[key] = product[key]
                    
                    # Specifically handle the palm oil field
                    if 'ingredients_from_palm_oil_n' in product:
                        nutrition_data['ingredients_from_palm_oil_n'] = product['ingredients_from_palm_oil_n']
                        logger.info(f"Palm oil ingredients count: {product['ingredients_from_palm_oil_n']}")
                    else:
                        # Make sure it's set to 0 if not found to avoid template errors
                        nutrition_data['ingredients_from_palm_oil_n'] = 0
                    
                    # For debugging, log what we got
                    if 'additives_tags' in product:
                        logger.info(f"Found {len(product['additives_tags'])} additives in API data")
                    else:
                        logger.warning("No additives_tags in API data")
                        
                    if 'ingredients_analysis_tags' in product:
                        logger.info(f"Found ingredients analysis tags: {product['ingredients_analysis_tags']}")
                    else:
                        logger.warning("No ingredients_analysis_tags in API data")
                    
                    # Store updated data in session
                    session['nutrition'] = nutrition_data
            except Exception as e:
                logger.error(f"Error fetching product data: {str(e)}")
                flash("Could not fetch latest product data", "warning")
        
        # Make sure essential structures exist in nutrition_data to prevent template errors
        if 'additives_tags' not in nutrition_data:
            nutrition_data['additives_tags'] = []
            
        if 'ingredients_analysis_tags' not in nutrition_data:
            nutrition_data['ingredients_analysis_tags'] = []
            
        if 'ingredients_from_palm_oil_n' not in nutrition_data:
            nutrition_data['ingredients_from_palm_oil_n'] = 0
        
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
        
        # For debugging, check what data we're sending to the template
        logger.info(f"NOVA score: {nova_score}")
        if 'additives_tags' in nutrition_data:
            logger.info(f"Sending {len(nutrition_data['additives_tags'])} additives to template")
        else:
            logger.warning("No additives_tags in nutrition_data for template")
            
        if 'ingredients_analysis_tags' in nutrition_data:
            logger.info(f"Sending ingredients analysis tags: {nutrition_data['ingredients_analysis_tags']}")
        else:
            logger.warning("No ingredients_analysis_tags in nutrition_data for template")
        
        return render_template(
            'product_details.html',
            nutrition=nutrition_data,
            allergies=allergies,
            safety_review=safety_review,
            is_logged_in=is_logged_in,
            user_health=user_health,
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
        
        # Get barcode and product name
        barcode = session.get('barcode')
        product_name = session.get('product_name', 'Current Product')
        
        logger.info(f"Finding alternatives for product: {product_name}, barcode: {barcode}, score: {current_score}")
        
        alternatives = []
        
        if barcode:
            try:
                # Get alternatives from the same category with better scores
                logger.info("Calling get_alternatives_by_category function")
                category_alternatives = get_alternatives_by_category(barcode, current_score)
                
                logger.info(f"Received {len(category_alternatives) if category_alternatives else 0} alternatives from search")
                
                if category_alternatives and isinstance(category_alternatives, list):
                    alternatives.extend(category_alternatives)
            except Exception as e:
                logger.error(f"Error getting category alternatives: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("No barcode available, skipping alternatives search")
        
        # If no alternatives found or error occurred, provide healthy generic alternatives
        if not alternatives:
            logger.info("No alternatives found from API, using generic alternatives")
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
        
        logger.info(f"Rendering template with {len(alternatives)} alternatives")
        
        return render_template(
            "alternative_products.html", 
            alternatives=alternatives,
            current_product=product_name
        )
        
    except Exception as e:
        logger.error(f"Error finding alternatives: {str(e)}")
        flash("An error occurred while finding alternatives. Please try again.", "error")
        return redirect(url_for('product.product_details'))

@product_bp.route('/nutrition')
def nutrition_landing():
    return render_template('nutrition_landing.html')

@product_bp.route('/barcode_lookup')
def barcode_lookup():
    return render_template('barcode_lookup.html') 