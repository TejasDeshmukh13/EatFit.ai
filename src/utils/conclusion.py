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

def check_product_safety(nutrition_data, health_data):
    """
    Check if product is safe based on user's health data
    
    Args:
        nutrition_data (dict): Product nutrition values
        health_data (dict): User health data including age, bmi, etc.
    
    Returns:
        dict: Safety review with conclusions and specific nutrient warnings
    """
    if not nutrition_data or not health_data or df_nutrients is None:
        return {
            "conclusion": "Unable to analyze product safety - insufficient data",
            "warnings": [],
            "safe_nutrients": []
        }

    try:
        age_column = get_age_column(health_data.get("age", 25))
        warnings = []
        safe_nutrients = []
        health_conditions = []
        
        # Check health conditions
        if health_data.get("diabetes"):
            health_conditions.append("diabetes")
        if health_data.get("cholesterol"):
            health_conditions.append("high cholesterol")
        if health_data.get("bp"):
            health_conditions.append("high blood pressure")
        
        # Map nutrition data keys to dataset names
        nutrient_mapping = {
            "fat": "fat",
            "saturated_fat": "saturated fat",
            "carbohydrates": "carbohydrates",
            "sugars": "sugar",
            "fiber": "fiber",
            "protein": "protein",
            "salt": "salt",
            "cholesterol": "cholesterol",
            "trans_fat": "trans fat"
        }

        critical_warnings = 0
        moderate_warnings = 0

        for nutrient_key, dataset_name in nutrient_mapping.items():
            value = nutrition_data.get(nutrient_key, 0)
            if value is None or value == 0:
                continue

            row = df_nutrients[df_nutrients["Nutrient/chemicals to avoid"].str.lower() == dataset_name]
            if row.empty:
                continue

            limit_str = str(row[age_column].values[0]).strip()
            
            # Handle different limit formats
            if "avoid" in limit_str.lower() or limit_str == "0" or re.match(r"0\s*[gmg]*", limit_str, re.IGNORECASE):
                limit = 0
            else:
                if "-" in limit_str:
                    parts = limit_str.split("-")
                    lower_bound = extract_numeric(parts[0])
                    upper_bound = extract_numeric(parts[1]) if len(parts) > 1 else lower_bound
                    limit = upper_bound
                else:
                    limit = extract_numeric(limit_str)

            # Check against health conditions
            is_risky = False
            if health_data.get("diabetes") and dataset_name in ["sugar", "carbohydrates"]:
                is_risky = True
                warning = f"High {dataset_name} content ({value}g) - Exercise caution due to diabetes"
                warnings.append(warning)
                critical_warnings += 1
            elif health_data.get("cholesterol") and dataset_name in ["cholesterol", "saturated fat", "trans fat"]:
                is_risky = True
                warning = f"High {dataset_name} content ({value}g) - Monitor intake due to cholesterol condition"
                warnings.append(warning)
                critical_warnings += 1
            elif health_data.get("bp") and dataset_name == "salt":
                is_risky = True
                warning = f"High {dataset_name} content ({value}g) - Limit intake due to high blood pressure"
                warnings.append(warning)
                critical_warnings += 1

            # Evaluate against limits
            if not is_risky:  # Only check limits if not already flagged for health condition
                if limit_str.startswith("≤") or limit == 0:
                    if value > limit:
                        warning = f"{dataset_name.title()} content ({value}g) exceeds recommended limit ({limit}g)"
                        warnings.append(warning)
                        moderate_warnings += 1
                    else:
                        # Only add to safe nutrients if the value is non-zero and within limits
                        if value > 0:
                            safe_nutrients.append(f"{dataset_name.title()} ({value}g)")
                elif limit_str.startswith("≥"):
                    if value < limit:
                        warning = f"{dataset_name.title()} content ({value}g) is below recommended value ({limit}g)"
                        warnings.append(warning)
                        moderate_warnings += 1
                    else:
                        # Only add to safe nutrients if the value meets or exceeds the minimum
                        safe_nutrients.append(f"{dataset_name.title()} ({value}g)")

        # Generate personalized conclusion
        if health_conditions:
            conditions_text = ", ".join(health_conditions)
            if critical_warnings > 0:
                conclusion = f"⚠️ Exercise caution with this product. Given your {conditions_text}, some nutrients exceed recommended limits."
            else:
                conclusion = f"✓ This product appears manageable with your {conditions_text}, but monitor your portions."
        else:
            if critical_warnings > 0:
                conclusion = "⚠️ Some nutrients in this product exceed recommended limits. Consider alternatives."
            elif moderate_warnings > 0:
                conclusion = "⚡ This product is acceptable but some nutrients are close to recommended limits."
            else:
                conclusion = "✓ This product appears safe for consumption based on your health profile."

        # Add specific advice about safe nutrients only if we found some
        if safe_nutrients:
            conclusion += f"\n\nNutrients within safe limits: {', '.join(safe_nutrients)}."

        return {
            "conclusion": conclusion,
            "warnings": warnings,
            "safe_nutrients": safe_nutrients
        }
        
    except Exception as e:
        logger.error(f"Error in safety analysis: {str(e)}")
        return {
            "conclusion": "Unable to complete safety analysis due to an error.",
            "warnings": [],
            "safe_nutrients": []
        } 