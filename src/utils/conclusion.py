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
    
    # Standardize nutrition data keys to match dataset
    nutrient_mapping = {
        'carbohydrates': ['carbohydrates_100g', 'carbohydrates'],
        'sugar': ['sugars_100g', 'sugars'],
        'saturated_fat': ['saturated-fat_100g', 'saturated_fat'],
        'trans_fat': ['trans-fat_100g', 'trans_fat'],
        'sodium': ['sodium_100g', 'sodium'],
        'salt': ['salt_100g', 'salt'],
        'cholesterol': ['cholesterol_100g', 'cholesterol'],
        'fiber': ['fiber_100g', 'fiber'],
        'protein': ['proteins_100g', 'protein'],
        'fat': ['fat_100g', 'fat'],
        'energy_kcal': ['energy-kcal_100g', 'energy-kcal', 'energy_kcal']
    }
    
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
            
            # Skip rows that don't match our nutrient keys
            nutrient_key = None
            for key in nutrient_mapping.keys():
                if key.lower() in nutrient.lower() or nutrient.lower() in key.lower():
                    nutrient_key = key
                    break
            
            if not nutrient_key:
                continue
                
            analyzed_nutrients.add(nutrient_key)
            
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
                elif operator in ['≥', '>'] and product_value < limit_num:
                    if "no" in strict_avoid.lower() and product_value > 0:
                        # For nutrients that should be higher (like fiber, protein)
                        # Only include if the value is greater than 0
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
    
    # Find nutrients that weren't analyzed
    for nutrient in nutrient_mapping.keys():
        if nutrient not in analyzed_nutrients and product_nutrients.get(nutrient, 0) > 0:
            not_analyzed.append({
                'nutrient': nutrient,
                'value': product_nutrients[nutrient]
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
        warning_text = f"High {item['nutrient']} content ({item['value']}g) - Exceeds recommended limit ({item['limit']}g) for your {item['condition']}"
        warnings.append(warning_text)
    
    # Add safe nutrients
    for item in nutrient_analysis['safe_nutrients']:
        if 'good' in item['recommendation'].lower():
            safe_nutrients.append(item['recommendation'])
    
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
        conditions = []
        if user_health.get('diabetes', False):
            conditions.append("diabetes")
        if user_health.get('bp', False):
            conditions.append("high blood pressure")
        if user_health.get('cholesterol', False):
            conditions.append("high cholesterol")
            
        conditions_text = " and ".join(conditions)
        
        if len(warnings) > 2:
            conclusion = f"⚠️ Caution with this product. Given your {conditions_text}, some nutrients exceed recommended limits."
        else:
            conclusion = f"⚠️ Consider limiting this product. Some nutrients may affect your {conditions_text}."
    elif len(safe_nutrients) > 0:
        conclusion = "✅ This product contains beneficial nutrients that align well with your health profile."
    
    return {
        "conclusion": conclusion,
        "warnings": warnings,
        "safe_nutrients": safe_nutrients
    } 