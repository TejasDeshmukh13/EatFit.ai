"""
Nutrition data parsing and scoring utilities.
"""
import re
import requests
import json
from utils.image_processing import extract_text
import logging
from models.food_analysis import get_product_from_off

logger = logging.getLogger(__name__)

def get_alternatives_by_category(barcode, current_grade):
    """
    Get alternative products with better nutri-scores from the same category
    """
    try:
        # First, get the product details to find its category
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get product details for barcode {barcode}")
            return []
            
        data = response.json()
        
        if data.get('status') != 1 or 'product' not in data:
            logger.warning(f"Invalid product data received for barcode {barcode}")
            return []
            
        product = data['product']
        
        # Get categories to search
        categories = []
        if 'categories_hierarchy' in product:
            categories.extend(product['categories_hierarchy'][:2])  # Get first two levels
        if 'categories_tags' in product:
            categories.extend(product['categories_tags'][:2])  # Get first two category tags
        
        # Remove duplicates while preserving order
        categories = list(dict.fromkeys(categories))
        
        if not categories:
            logger.warning(f"No categories found for product {barcode}")
            return []
        
        # Get current product details for comparison
        current_product = {
            'nutrients': product.get('nutriments', {}),
            'nova_group': product.get('nova_group'),
            'nutriscore_grade': product.get('nutrition_grades', current_grade)
        }
        
        alternatives = []
        target_grades = ['a', 'b']  # Look for A and B rated products
        
        for category in categories:
            try:
                # Search for alternatives
                search_url = "https://world.openfoodfacts.org/cgi/search.pl"
                params = {
                    'action': 'process',
                    'tagtype_0': 'categories',
                    'tag_contains_0': 'contains',
                    'tag_0': category,
                    'tagtype_1': 'nutrition_grades',
                    'tag_contains_1': 'contains',
                    'tag_1': target_grades,
                    'sort_by': 'unique_scans_n',
                    'page_size': 10,
                    'json': 1
                }
                
                search_response = requests.get(search_url, params=params, timeout=15)
                
                if search_response.status_code != 200:
                    continue
                    
                search_data = search_response.json()
                
                for alt_product in search_data.get('products', []):
                    # Skip if it's the same product or missing key data
                    if (alt_product.get('code') == barcode or
                        not alt_product.get('product_name') or
                        not alt_product.get('image_url') or
                        not alt_product.get('nutriments')):
                        continue
                    
                    # Calculate improvements over current product
                    improvements = []
                    
                    # Compare Nutri-Score
                    alt_score = alt_product.get('nutrition_grades', '').lower()
                    if alt_score in target_grades and (not current_grade or alt_score < current_grade.lower()):
                        improvements.append(f"Better Nutri-Score ({alt_score.upper()})")
                    
                    # Compare NOVA score
                    alt_nova = alt_product.get('nova_group')
                    current_nova = current_product['nova_group']
                    if alt_nova and current_nova and alt_nova < current_nova:
                        improvements.append("Less processed")
                    
                    # Compare key nutrients
                    alt_nutrients = alt_product.get('nutriments', {})
                    current_nutrients = current_product['nutrients']
                    
                    nutrient_comparisons = [
                        ('sugars_100g', 'sugar', '<'),
                        ('salt_100g', 'salt', '<'),
                        ('fiber_100g', 'fiber', '>'),
                        ('proteins_100g', 'protein', '>')
                    ]
                    
                    for nutrient_key, nutrient_name, comparison in nutrient_comparisons:
                        alt_value = alt_nutrients.get(nutrient_key, 0)
                        current_value = current_nutrients.get(nutrient_key, 0)
                        
                        if current_value > 0:  # Only compare if current product has this nutrient
                            if comparison == '<' and alt_value < current_value:
                                improvements.append(f"Lower in {nutrient_name}")
                            elif comparison == '>' and alt_value > current_value:
                                improvements.append(f"Higher in {nutrient_name}")
                    
                    # Only add product if we found improvements
                    if improvements:
                        alternative = {
                            'product_name': alt_product['product_name'],
                            'brand': alt_product.get('brands', 'Unknown Brand'),
                            'image_url': alt_product['image_url'],
                            'nutriscore_grade': alt_score.upper(),
                            'nova_group': alt_nova,
                            'reason': " • ".join(improvements[:3]),  # Top 3 improvements
                            'is_indian': False
                        }
                        
                        # Add to alternatives if not already present
                        if not any(a['product_name'] == alternative['product_name'] for a in alternatives):
                            alternatives.append(alternative)
                    
                    # Limit to top 6 alternatives
                    if len(alternatives) >= 6:
                        break
                
                if len(alternatives) >= 6:
                    break
                    
            except Exception as e:
                logger.error(f"Error searching category {category}: {str(e)}")
                continue
        
        return alternatives[:6]  # Return top 6 alternatives
            
    except Exception as e:
        logger.error(f"Error finding alternatives: {str(e)}")
        return []

def parse_nutrition(text):
    """
    Parse nutrition information from text.
    """
    # Energy patterns with parentheses support
    energy_matches = re.findall(
        r'(?:Energy\s*\(?kcal\)?.*?)(\d+\.?\d*)|'
        r'(\d+\.?\d*)\s*\(?kcal\)?(?=\s|$)',
        text,
        re.IGNORECASE
    )
    
    energy_values = [float(m[0] or m[1]) for m in energy_matches if any(m)]
    
    nutrition = {
        'energy_kcal': energy_values[0] if energy_values else None,
        'sugars': None,
        'salt': None
    }

    sugar_patterns = [
        r'(of\s*which\s*sugars.*?)(\d+\.?\d*)\s*g',
        r'\bsugars?\b.*?(\d+\.?\d*)\s*g'
    ]
    for pattern in sugar_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                nutrition['sugars'] = float(match.group(1))
                break
            except:
                continue

    sodium_match = re.search(r'sodium.*?(\d+\.?\d*)\s*mg', text, re.IGNORECASE)
    if sodium_match:
        try:
            sodium_mg = float(sodium_match.group(1))
            nutrition['salt'] = sodium_mg / 400  # Convert to grams
        except:
            pass
    
    salt_match = re.search(r'salt.*?(\d+\.?\d*)\s*g', text, re.IGNORECASE)
    if salt_match and not nutrition['salt']:
        try:
            nutrition['salt'] = float(salt_match.group(1))
        except:
            pass

    nutrient_patterns = {
        'fat': r'(Total Fat|Fat)[^\d]*(\d+\.?\d*)',
        'saturated_fat': r'(Saturates|Saturated Fat)[^\d]*(\d+\.?\d*)',
        'carbohydrates': r'(Carbohydrates|Carbs)[^\d]*(\d+\.?\d*)',
        'fiber': r'(Fibre|Fiber)[^\d]*(\d+\.?\d*)',
        'protein': r'Protein[^\d]*(\d+\.?\d*)'
    }
    
    for nutrient, pattern in nutrient_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                nutrition[nutrient] = float(match.group(2))
            except:
                continue
    
    return nutrition

def merge_nutrition_data(ocr_data, api_data):
    """
    Merge nutrition data from OCR and API, preferring API data when available.
    """
    # Start with OCR data
    merged = ocr_data.copy()
    
    # For each field, use API data if it exists and OCR data is missing or zero
    for key, api_value in api_data.items():
        # Skip error field
        if key == 'error':
            continue
            
        # For nutrition values, handle numeric comparison
        if key in ['energy_kcal', 'fat', 'saturated_fat', 'carbohydrates', 'sugars', 'fiber', 'protein', 'salt']:
            # Convert to float for comparison
            try:
                api_value = float(api_value) if api_value is not None else 0
            except (ValueError, TypeError):
                api_value = 0
                
            # Use API value if:
            # 1. OCR value doesn't exist or is None
            # 2. OCR value is 0 and API value is greater than 0
            if key not in merged or merged[key] is None or (merged[key] == 0 and api_value > 0):
                merged[key] = api_value
        # For non-numeric fields, always prefer API data if present
        elif key in ['product_name', 'brand', 'categories', 'image_url', 'ingredients_text', 
                      'additives_tags', 'ingredients_analysis_tags', 'nova_group', 'nova_score']:
            if api_value:  # Only add if not empty/None
                merged[key] = api_value
    
    # Add computed scores from API if available
    if 'nova_score' in api_data:
        merged['nova_score'] = api_data['nova_score']
    
    return merged

def process_with_config(image_path, config_idx, barcode=None):
    """
    Process image with a specific OCR configuration and extract nutrition data.
    Optionally use barcode to fetch data from Open Food Facts API.
    """
    nutrition_data = {}
    api_data = {}
    ocr_data = {}
    
    try:
        # Try to get data from API if barcode is provided
        if barcode:
            # Get product data from the OpenFoodFacts API
            product = get_product_from_off(barcode)
            
            # Process the product data if found
            if product:
                # Extract nutrition data
                nutrients = product.get('nutriments', {})
                
                # Create nutrition data dictionary
                api_data = {
                    'product_name': product.get('product_name', 'Unknown Product'),
                    'brand': product.get('brands', 'Unknown Brand'),
                    'energy_kcal': float(nutrients.get('energy-kcal_100g', 0)),
                    'fat': float(nutrients.get('fat_100g', 0)),
                    'saturated_fat': float(nutrients.get('saturated-fat_100g', 0)),
                    'carbohydrates': float(nutrients.get('carbohydrates_100g', 0)),
                    'sugars': float(nutrients.get('sugars_100g', 0)),
                    'fiber': float(nutrients.get('fiber_100g', 0)),
                    'protein': float(nutrients.get('proteins_100g', 0)),
                    'salt': float(nutrients.get('salt_100g', 0)),
                    'categories': product.get('categories', ''),
                    'image_url': product.get('image_url', ''),
                    'ingredients_text': product.get('ingredients_text', ''),
                    'additives_tags': product.get('additives_tags', []),
                    'ingredients_analysis_tags': product.get('ingredients_analysis_tags', []),
                    'nova_group': product.get('nova_group', 4),
                    'nova_score': product.get('nova_groups', 4),
                }
                
                nutrition_data = api_data.copy()
                
                # Use official scores from API if available
                if api_data.get('nova_group'):
                    # Use the comprehensive get_nova_score function for score details
                    nova_score_details = get_nova_score(api_data)
                    nutrition_data['nova_score'] = nova_score_details
                    
                    # Add processing information to the nutrition data
                    nutrition_data['processing'] = {
                        'nova_group': nova_score_details['score'],
                        'nova_explanation': nova_score_details['nova_explanation'],
                        'markers_explanation': nova_score_details['markers_explanation']
                    }
            else:
                # If product not found, set an error
                api_data = {'error': 'Product not found in database'}
        
        # Extract data from image using OCR
        ocr_data = extract_text(image_path)
        
        # If we have both OCR and API data, merge them
        if ocr_data and 'error' not in api_data and barcode:
            nutrition_data = merge_nutrition_data(ocr_data, api_data)
        # If we only have OCR data (no barcode or API failed)
        elif ocr_data and (not barcode or 'error' in api_data):
            nutrition_data = ocr_data
        # If OCR failed but we have API data
        elif not ocr_data and 'error' not in api_data and barcode:
            nutrition_data = api_data
        # If both failed, provide default values
        elif not nutrition_data:
            nutrition_data = {
                "energy_kcal": 0,
                "fat": 0,
                "saturated_fat": 0,
                "carbohydrates": 0,
                "sugars": 0,
                "fiber": 0,
                "protein": 0,
                "salt": 0
            }
            
            # If API had an error, include it
            if barcode and 'error' in api_data:
                nutrition_data['api_error'] = api_data['error']
        
        return nutrition_data
    except Exception as e:
        print(f"Error in process_with_config: {str(e)}")
        return {"error": str(e)}

def calculate_nutri_score(nutrition):
    """
    Calculate Nutri-Score grade based on Indian nutrition guidelines.
    
    This implements a simplified version of nutrition scoring based on 
    Indian food packaging standards (FSSAI guidelines).
    """
    # Convert any None values to 0 for comparisons
    energy = float(nutrition.get('energy_kcal', 0) or 0)
    sugars = float(nutrition.get('sugars', 0) or 0)
    fat = float(nutrition.get('fat', 0) or 0)
    saturated_fat = float(nutrition.get('saturated_fat', 0) or 0)
    salt = float(nutrition.get('salt', 0) or 0)
    protein = float(nutrition.get('protein', 0) or 0)
    fiber = float(nutrition.get('fiber', 0) or 0)
    
    # Initialize score (lower is better in our simplified approach)
    unfavorable_points = 0
    favorable_points = 0
    
    # Score unfavorable nutrients (based on Indian RDA values)
    # Energy
    if energy > 400:
        unfavorable_points += 2
    elif energy > 200:
        unfavorable_points += 1
    
    # Sugars (per serving)
    if sugars > 15:
        unfavorable_points += 3
    elif sugars > 9:
        unfavorable_points += 2
    elif sugars > 4.5:
        unfavorable_points += 1
    
    # Total Fat
    if fat > 18:
        unfavorable_points += 3
    elif fat > 10:
        unfavorable_points += 2
    elif fat > 3:
        unfavorable_points += 1
    
    # Saturated Fat
    if saturated_fat > 6:
        unfavorable_points += 3
    elif saturated_fat > 3:
        unfavorable_points += 2
    elif saturated_fat > 1:
        unfavorable_points += 1
    
    # Salt/Sodium
    if salt > 1.5:
        unfavorable_points += 3
    elif salt > 0.8:
        unfavorable_points += 2
    elif salt > 0.3:
        unfavorable_points += 1
    
    # Score favorable nutrients
    # Protein
    if protein > 12:
        favorable_points += 3
    elif protein > 6:
        favorable_points += 2
    elif protein > 3:
        favorable_points += 1
    
    # Fiber
    if fiber > 7:
        favorable_points += 3
    elif fiber > 4:
        favorable_points += 2
    elif fiber > 2:
        favorable_points += 1
    
    # Calculate final score
    final_score = unfavorable_points - favorable_points
    
    # Assign grade
    if final_score <= -2:
        return 'A'  # Very good nutritional quality
    elif final_score <= 0:
        return 'B'  # Good nutritional quality
    elif final_score <= 3:
        return 'C'  # Average nutritional quality
    elif final_score <= 6:
        return 'D'  # Poor nutritional quality
    else:
        return 'E'  # Very poor nutritional quality

def get_nova_score(nutrition_data):
    """
    Get NOVA score for food processing level.
    Returns a dictionary with score details.
    
    NOVA Groups:
    1 - Unprocessed or minimally processed foods
    2 - Processed culinary ingredients
    3 - Processed foods
    4 - Ultra-processed foods
    """
    # Get NOVA group from API data
    nova_group = nutrition_data.get('nova_group', 4)  # Default to 4 if not specified
    
    # Ensure nova_group is an integer between 1 and 4
    try:
        nova_group = int(nova_group)
        nova_group = max(1, min(4, nova_group))
    except (ValueError, TypeError):
        nova_group = 4  # Default to ultra-processed if invalid
    
    # Define descriptions and explanations
    descriptions = {
        1: "Unprocessed or minimally processed foods",
        2: "Processed culinary ingredients",
        3: "Processed foods",
        4: "Ultra-processed foods"
    }
    
    explanations = {
        1: "NOVA score 1 indicates unprocessed or minimally processed foods that are natural and have undergone minimal alterations.",
        2: "NOVA score 2 indicates processed culinary ingredients like oils, butter, and sugar that are derived from natural foods through processes like pressing or refining.",
        3: "NOVA score 3 indicates moderately processed foods with additives for preservation or to enhance taste, but still recognizable as derived from real foods.",
        4: "NOVA score 4 indicates ultra-processed foods with multiple ingredients including additives not typically used in home cooking, often designed to be convenient and highly palatable."
    }
    
    markers_explanation = "Ultra-processing markers are indicators of industrial processes applied to foods, such as additives, artificial flavors, hydrogenated oils, and preservatives."
    
    # Set the marker count based on the NOVA group
    markers_count = 0
    if nova_group == 3:
        markers_count = 1
    elif nova_group == 4:
        markers_count = 2
    
    return {
        'score': nova_group,
        'description': descriptions[nova_group],
        'markers_count': markers_count,
        'nova_explanation': explanations[nova_group],
        'markers_explanation': markers_explanation
    } 