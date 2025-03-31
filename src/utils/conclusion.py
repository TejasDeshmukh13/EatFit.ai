import pandas as pd
import os
import re
import logging
from flask import g

# Set up logging
logger = logging.getLogger(__name__)

# Load nutrients dataset with the exact filename
try:
    df_nutrients = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nutrients-dataset.csv"), encoding="utf-8-sig")
    logger.info("Successfully loaded nutrients dataset")
except Exception as e:
    logger.error(f"Error loading nutrients dataset: {str(e)}")
    df_nutrients = None

def get_age_column(age):
    """Determine age group column based on age"""
    if 0 <= age <= 6:
        return "0-6 years"
    elif 7 <= age <= 12:
        return "7-12 years"
    elif 13 <= age <= 18:
        return "13-18 years"
    else:
        return "Adults"

def extract_numeric(value):
    """Extract numeric value from string"""
    try:
        return float(re.sub(r"[^\d.]", "", str(value)))
    except ValueError:
        return 0

def check_nutrient_limits(nutrition_data, user_health):
    """
    Compare product nutrients with recommended limits from the nutrients-dataset.csv
    based on user's health conditions and age.
    
    Args:
        nutrition_data (dict): Product nutrition data
        user_health (dict): User health profile
        
    Returns:
        dict: Detailed analysis of nutrients compared to recommended limits
    """
    if df_nutrients is None or not user_health:
        return {
            'exceeded_limits': [],
            'safe_nutrients': [],
            'not_analyzed': []
        }
    
    # Determine user's health conditions
    conditions = []
    if user_health.get('diabetes', False):
        if user_health.get('bp', False) and user_health.get('cholesterol', False):
            conditions.append("Type 2 diabetes") # More comprehensive limits for multiple conditions
        else:
            conditions.append("Type 1 diabetes")
    
    if user_health.get('bp', False):
        conditions.append("hypertension(high bp)")
    
    if user_health.get('cholesterol', False):
        conditions.append("High Cholesterol")
    
    # If no specific condition, use BMI category
    if not conditions:
        bmi = user_health.get('bmi', 22)
        if bmi < 18.5:
            conditions.append("underweight(bmi<18.5)")
        elif 18.5 <= bmi < 25:
            conditions.append("normal(bmi 18.5-24.9)")
        elif 25 <= bmi < 30:
            conditions.append("Overweight (BMI 25-29.9)")
        else:
            # If BMI > 30, add obesity which will be handled via general nutrient guidelines
            conditions.append("Overweight (BMI 25-29.9)")  # Using overweight limits for now
    
    # Get age group column
    age_column = get_age_column(user_health.get('age', 30))
    
    # Build nutrient mapping dynamically from the dataset
    # First, get all unique nutrients from the dataset
    all_nutrients = df_nutrients['Nutrient/chemicals to avoid'].dropna().unique()
    
    # Create a base mapping for common nutrients with known keys
    base_mapping = {
        'carbohydrates': ['carbohydrates_100g', 'carbohydrates'],
        'sugar': ['sugars_100g', 'sugars'],
        'saturated_fat': ['saturated-fat_100g', 'saturated_fat'],
        'sodium': ['sodium_100g', 'sodium'],
        'salt': ['salt_100g', 'salt'],
        'cholesterol': ['cholesterol_100g', 'cholesterol'],
        'fiber': ['fiber_100g', 'fiber'],
        'protein': ['proteins_100g', 'protein'],
        'fat': ['fat_100g', 'fat'],
        'energy_kcal': ['energy-kcal_100g', 'energy-kcal', 'energy_kcal'],
    }
    
    # Now build the complete mapping by including all nutrients from the dataset
    nutrient_mapping = base_mapping.copy()
    
    # Map common formats for nutrient keys in API data
    for nutrient in all_nutrients:
        nutrient_key = nutrient.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
        
        # Skip if already in base mapping or if it's trans fat (which we want to exclude)
        if nutrient_key in base_mapping or 'trans' in nutrient_key or 'trans' in nutrient.lower():
            continue
            
        # Create possible variations for this nutrient's keys
        variants = [
            f"{nutrient_key}_100g",
            nutrient_key,
            nutrient_key.replace('_', '-'),
            nutrient.lower()
        ]
        
        # Special handling for specific nutrient types
        if "vitamin" in nutrient_key:
            vitamin_name = nutrient_key.replace('vitamin_', '')
            variants.extend([
                f"vitamin-{vitamin_name}_100g",
                f"vitamin_{vitamin_name}",
                f"vitamin-{vitamin_name}"
            ])
        elif "omega" in nutrient_key:
            omega_number = nutrient_key.replace('omega_', '')
            variants.extend([
                f"omega-{omega_number}-fat_100g",
                f"omega_{omega_number}",
                f"omega-{omega_number}"
            ])
        
        # Add to mapping if not already present
        if nutrient_key not in nutrient_mapping:
            nutrient_mapping[nutrient_key] = variants
    
    # Extract nutrient values from product data
    product_nutrients = {}
    for nutrient, keys in nutrient_mapping.items():
        for key in keys:
            if key in nutrition_data:
                value = nutrition_data[key]
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
                    product_nutrients[nutrient] = float(value)
                    break
        
        # Set default value if not found
        if nutrient not in product_nutrients:
            product_nutrients[nutrient] = 0
    
    # Results containers
    exceeded_limits = []
    safe_nutrients = []
    not_analyzed = []
    
    # For each condition, check nutrient limits
    analyzed_nutrients = set()
    processed_nutrients = set()  # Track which nutrients we've already processed
    
    for condition in conditions:
        condition_df = df_nutrients[df_nutrients['TYPE'] == condition]
        
        if condition_df.empty:
            logger.warning(f"No data found for condition: {condition}")
            continue
        
        # Check each nutrient's limits for this condition
        for _, row in condition_df.iterrows():
            nutrient = row['Nutrient/chemicals to avoid'].lower()
            limit_value = row[age_column]
            strict_avoid = row['Strictly Avoid?'].lower() if not pd.isna(row['Strictly Avoid?']) else "no"
            
            # Generate a standardized key for this nutrient
            nutrient_std_key = nutrient.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
            
            # Skip rows that don't match our nutrient keys
            nutrient_key = None
            
            # Try exact match first
            for key in nutrient_mapping:
                # Exact match check
                if key == nutrient_std_key:
                    nutrient_key = key
                    break
                    
                # Check for partial matches with special handling
                is_partial_match = (
                    (nutrient in key or key in nutrient) and 
                    # Prevent confusion between similar nutrients
                    not (key == 'fat' and ('trans' in nutrient or 'saturated' in nutrient)) and
                    not (key == 'trans_fat' and nutrient == 'fat') and
                    not (key == 'saturated_fat' and nutrient == 'fat') and
                    not (key == 'sugar' and 'sweetener' in nutrient) and
                    not (key == 'artificial_sweeteners' and nutrient == 'sugar')
                )
                
                if is_partial_match:
                    nutrient_key = key
                    break
            
            if not nutrient_key or nutrient in processed_nutrients:
                continue
                
            analyzed_nutrients.add(nutrient_key)
            processed_nutrients.add(nutrient)  # Mark as processed to avoid duplicates
            
            # Extract numeric value and comparison operator from limit
            numeric_match = re.search(r'([≤≥<>])\s*(\d+\.?\d*)', str(limit_value))
            if numeric_match:
                operator = numeric_match.group(1)
                limit_num = float(numeric_match.group(2))
                
                product_value = product_nutrients.get(nutrient_key, 0)
                
                # Compare based on operator
                if operator in ['≤', '<'] and product_value > limit_num:
                    exceeded_limits.append({
                        'nutrient': nutrient,
                        'value': product_value,
                        'limit': limit_num,
                        'condition': condition,
                        'recommendation': strict_avoid
                    })
                elif operator in ['≤', '<'] and product_value <= limit_num and product_value > 0:
                    # For nutrients that should be lower (like sugar, salt)
                    # Include them as safe if they're below the limit
                    safe_nutrients.append({
                        'nutrient': nutrient,
                        'value': product_value,
                        'recommendation': f"Good intake of {nutrient} ({product_value}g)"
                    })
                elif operator in ['≥', '>'] and product_value < limit_num:
                    if "no" in strict_avoid.lower() and product_value > 0:
                        # For nutrients that should be higher (like fiber, protein)
                        # Only include if the value is greater than 0
                        safe_nutrients.append({
                            'nutrient': nutrient,
                            'value': product_value,
                            'recommendation': f"Good intake of {nutrient} ({product_value}g)"
                        })
                elif operator in ['≥', '>'] and product_value >= limit_num:
                    # Nutrient is at or above the recommended minimum
                    if product_value > 0:  # Only include if the value is greater than 0
                        safe_nutrients.append({
                            'nutrient': nutrient,
                            'value': product_value,
                            'recommendation': f"Good intake of {nutrient} ({product_value}g)"
                        })
                else:
                    # Nutrient is within acceptable limits
                    if product_value > 0:  # Only include if the value is greater than 0
                        safe_nutrients.append({
                            'nutrient': nutrient,
                            'value': product_value,
                            'recommendation': f"Acceptable level of {nutrient} ({product_value}g)"
                        })
            elif "avoid" in str(limit_value).lower() and product_value > 0:
                # For nutrients that should be avoided entirely
                exceeded_limits.append({
                    'nutrient': nutrient,
                    'value': product_value,
                    'limit': 0,
                    'condition': condition,
                    'recommendation': "Avoid"
                })
    
    # Find nutrients that weren't analyzed
    for nutrient, value in product_nutrients.items():
        if nutrient not in analyzed_nutrients and value > 0:
            not_analyzed.append({
                'nutrient': nutrient.replace('_', ' '),
                'value': value
            })
    
    return {
        'exceeded_limits': exceeded_limits,
        'safe_nutrients': safe_nutrients,
        'not_analyzed': not_analyzed
    }

def check_product_safety(nutrition_data, user_health):
    """
    Check if a product is safe for a person based on their health data.
    Returns warnings and safe components based on nutrients-dataset.csv analysis.
    """
    warnings = []
    safe_nutrients = []
    
    # Safe defaults
    conclusion = "✅ This product appears suitable for your health profile. Enjoy in moderation as part of a balanced diet."
    
    # Check if user health data is available
    if not user_health:
        return {
            "conclusion": "Log in and update your health profile for personalized recommendations.",
            "warnings": [],
            "safe_nutrients": []
        }
    
    # Get detailed nutrient analysis from dataset
    nutrient_analysis = check_nutrient_limits(nutrition_data, user_health)
    
    # Process exceeded limits as warnings
    for item in nutrient_analysis['exceeded_limits']:
        # Skip trans fat
        if 'trans' in item['nutrient'].lower():
            continue
            
        # Ensure we have accurate values, especially for saturated fat
        nutrient_value = item['value']
        
        # Special check for saturated fat which often has inconsistencies
        if 'saturated' in item['nutrient'].lower():
            # Check alternative keys for more accurate values
            sat_fat_keys = ['saturated-fat_100g', 'saturated_fat_100g', 'saturated_fat', 'saturated-fat']
            for key in sat_fat_keys:
                if key in nutrition_data and nutrition_data[key] != nutrient_value:
                    # If the value exists and is different, use it
                    if isinstance(nutrition_data[key], (int, float)) or (
                            isinstance(nutrition_data[key], str) and 
                            nutrition_data[key].replace('.', '', 1).isdigit()):
                        nutrient_value = float(nutrition_data[key])
                        break
        
        # Determine the appropriate unit based on the nutrient
        unit = "g"
        if "caffeine" in item['nutrient'].lower():
            unit = "mg"
        elif any(vitamin in item['nutrient'].lower() for vitamin in ["vitamin", "folate", "folic"]):
            unit = "μg"
        elif any(mineral in item['nutrient'].lower() for mineral in ["iron", "zinc", "selenium", "iodine", "magnesium", "calcium"]):
            unit = "mg"
        elif "glycemic" in item['nutrient'].lower():
            unit = ""  # No unit for glycemic index
        
        # Different message format for "Avoid" nutrients
        if item.get('recommendation') == "Avoid" or item.get('limit') == 0:
            warning_text = f"Contains {item['nutrient']} ({nutrient_value}{unit}) - Should be avoided"
        else:
            warning_text = f"High {item['nutrient']} content ({nutrient_value}{unit}) - Exceeds recommended limit ({item['limit']}{unit})"
        
        warnings.append(warning_text)
    
    # Add safe nutrients
    for item in nutrient_analysis['safe_nutrients']:
        # Skip trans fat
        if 'trans' in item['nutrient'].lower():
            continue
            
        if 'good' in item['recommendation'].lower() or 'acceptable' in item['recommendation'].lower():
            # Determine the appropriate unit based on the nutrient
            unit = "g"
            if "caffeine" in item['nutrient'].lower():
                unit = "mg"
            elif any(vitamin in item['nutrient'].lower() for vitamin in ["vitamin", "folate", "folic"]):
                unit = "μg"
            elif any(mineral in item['nutrient'].lower() for mineral in ["iron", "zinc", "selenium", "iodine", "magnesium", "calcium"]):
                unit = "mg"
            elif "glycemic" in item['nutrient'].lower():
                unit = ""  # No unit for glycemic index
            
            # Update the recommendation text with the correct unit
            if "{" in item['recommendation'] and "}" in item['recommendation']:
                # Replace the existing unit in the recommendation
                recommendation = item['recommendation'].replace("g)", f"{unit})")
            else:
                recommendation = item['recommendation']
            
            safe_nutrients.append(recommendation)
    
    # Ensure each unique nutrient is only listed once in safe_nutrients
    unique_safe_nutrients = []
    seen_nutrients = set()
    for nutrient in safe_nutrients:
        nutrient_name = nutrient.split(' of ')[1].split(' (')[0] if ' of ' in nutrient else nutrient
        if nutrient_name not in seen_nutrients:
            seen_nutrients.add(nutrient_name)
            unique_safe_nutrients.append(nutrient)
    
    safe_nutrients = unique_safe_nutrients
    
    # Update conclusion based on warnings
    if warnings:
        if len(warnings) > 2:
            conclusion = f"⚠️ Caution with this product. Some nutrients exceed recommended health limits."
        else:
            conclusion = f"⚠️ Consider limiting this product. Some nutrients exceed recommended limits."
    elif len(safe_nutrients) > 0:
        conclusion = "✅ This product contains beneficial nutrients that align well with your health profile."
    
    return {
        "conclusion": conclusion,
        "warnings": warnings,
        "safe_nutrients": safe_nutrients
    } 