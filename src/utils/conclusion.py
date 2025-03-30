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

def check_product_safety(nutrition_data, user_health):
    """
    Check if a product is safe for a person based on their health data.
    Returns warnings and safe components.
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
    
    # Check for diabetes
    if user_health.get('diabetes', False):
        # Check carbohydrates
        carbs = nutrition_data.get('carbohydrates_100g', nutrition_data.get('carbohydrates', 0))
        if carbs > 30:  # High carbs
            warnings.append(f"High carbohydrates content ({carbs}g) - Caution due to diabetes")
        
        # Check sugars
        sugars = nutrition_data.get('sugars_100g', nutrition_data.get('sugars', 0))
        if sugars > 5:  # High sugars
            warnings.append(f"High sugar content ({sugars}g) - Caution due to diabetes")
        
    # Check for high blood pressure
    if user_health.get('bp', False):
        # Check sodium/salt
        sodium = nutrition_data.get('sodium_100g', nutrition_data.get('sodium', 0))
        salt = nutrition_data.get('salt_100g', nutrition_data.get('salt', 0))
        
        # If salt is available, use it, otherwise calculate from sodium
        if salt > 0:
            if salt > 1.5:  # High salt
                warnings.append(f"High salt content ({salt}g) - Caution due to high blood pressure")
        elif sodium > 0:
            if sodium > 600:  # High sodium
                warnings.append(f"High sodium content ({sodium}mg) - Caution due to high blood pressure")
    
    # Check for high cholesterol
    if user_health.get('cholesterol', False):
        # Check saturated fat
        sat_fat = nutrition_data.get('saturated-fat_100g', nutrition_data.get('saturated_fat', 0))
        if sat_fat > 5:  # High saturated fat
            warnings.append(f"High saturated fat content ({sat_fat}g) - Caution due to high cholesterol")
            
        # Check total fat
        fat = nutrition_data.get('fat_100g', nutrition_data.get('fat', 0))
        if fat > 20:  # High fat
            warnings.append(f"High fat content ({fat}g) - Caution due to high cholesterol")
    
    # Check BMI if available
    # Note: these are very general guidelines
    bmi = user_health.get('bmi')
    if bmi and bmi > 30:  # Potential obesity
        # Check calories
        energy = nutrition_data.get('energy-kcal_100g', 
                                 nutrition_data.get('energy-kcal', 
                                                nutrition_data.get('energy_kcal', 0)))
        if energy > 350:  # High calorie
            warnings.append(f"High calorie content ({energy}kcal per 100g) - Be mindful of total intake")
            
        # Check fat
        fat = nutrition_data.get('fat_100g', nutrition_data.get('fat', 0))
        if fat > 15:  # High fat for weight management
            warnings.append(f"High fat content ({fat}g) - Consider limiting consumption")
    
    # Identify positive nutrients
    fiber = nutrition_data.get('fiber_100g', nutrition_data.get('fiber', 0))
    protein = nutrition_data.get('proteins_100g', nutrition_data.get('protein', 0))
    
    if fiber > 5:
        safe_nutrients.append(f"High in fiber ({fiber}g per 100g), which may help regulate blood sugar levels")
        
    if protein > 10:
        safe_nutrients.append(f"Good source of protein ({protein}g per 100g)")
    
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
    
    return {
        "conclusion": conclusion,
        "warnings": warnings,
        "safe_nutrients": safe_nutrients
    } 