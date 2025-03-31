import pandas as pd
import os
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default allergies data with more detailed information
DEFAULT_ALLERGIES_DATA = {
    "Ingredients": [
        "peanuts", "tree nuts", "milk", "eggs", "soy", "wheat", "fish", "shellfish",
        "sesame", "mustard", "celery", "lupin", "sulphites", "molluscs"
    ],
    "Allergies/Problems Caused": [
        "Peanut allergy - High risk of severe reactions including anaphylaxis",
        "Tree nut allergy - Common allergen that can cause severe reactions",
        "Milk allergy/Lactose intolerance - Can cause digestive issues and allergic reactions",
        "Egg allergy - Common in children, can affect both egg white and yolk",
        "Soy allergy - Found in many processed foods, can cause various reactions",
        "Wheat/Gluten sensitivity - May indicate celiac disease or gluten intolerance",
        "Fish allergy - Can cause severe reactions, often lifelong",
        "Shellfish allergy - Common in adults, high risk of severe reactions",
        "Sesame allergy - Increasingly common, can cause severe reactions",
        "Mustard allergy - Can cause reactions ranging from mild to severe",
        "Celery allergy - Including celery root, seeds, and leaves",
        "Lupin allergy - Related to peanut allergy, found in some flours",
        "Sulphite sensitivity - Can trigger asthma and other reactions",
        "Mollusc allergy - Including mussels, oysters, and squid"
    ]
}

# Load the allergies dataset
try:
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "food allergies.csv")
    if os.path.exists(csv_path):
        df_allergies = pd.read_csv(csv_path)
        logger.info("Successfully loaded allergies data from CSV file")
    else:
        df_allergies = pd.DataFrame(DEFAULT_ALLERGIES_DATA)
        logger.warning("CSV file not found. Using default allergies data")
except Exception as e:
    logger.error(f"Error loading allergies data: {str(e)}")
    df_allergies = pd.DataFrame(DEFAULT_ALLERGIES_DATA)

def fetch_ingredients_from_barcode(barcode):
    """Fetch ingredients from Open Food Facts API"""
    api_url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        response = requests.get(api_url)
        data = response.json()
        
        if data.get("status") == 1:  # Product found
            ingredients_text = data["product"].get("ingredients_text", "")
            ingredient_list = [ing.strip() for ing in ingredients_text.split(",") if ing.strip()]
            return ingredient_list
        return None
    except Exception as e:
        logger.error(f"Error fetching ingredients: {str(e)}")
        return None

def clean_ingredient(ingredient):
    """Clean ingredient text for better matching"""
    return ingredient.lower().strip().replace('-', ' ').replace('_', ' ')

def get_ingredient_variations(ingredient):
    """Generate common variations of ingredient names"""
    clean_ing = clean_ingredient(ingredient)
    variations = {clean_ing}
    
    # Common ingredient variations dictionary
    variations_dict = {
        'milk': ['dairy', 'lactose', 'whey', 'casein', 'cream'],
        'wheat': ['gluten', 'flour', 'semolina', 'spelt', 'rye', 'barley'],
        'egg': ['eggs', 'albumen', 'lecithin', 'lysozyme', 'globulin'],
        'soy': ['soya', 'soybeans', 'tofu', 'edamame'],
        'fish': ['salmon', 'tuna', 'cod', 'anchovy', 'sardine'],
        'nuts': ['almond', 'cashew', 'walnut', 'pecan', 'hazelnut', 'macadamia'],
        'peanut': ['groundnut', 'arachis'],
        'shellfish': ['shrimp', 'crab', 'lobster', 'prawn'],
        'sesame': ['tahini', 'sesame oil', 'sesame seed'],
        'celery': ['celeriac', 'celery root', 'celery salt'],
        'mustard': ['mustard seed', 'mustard oil', 'mustard powder'],
        'sulphites': ['sulfites', 'e220', 'e228'],
        'lupin': ['lupini', 'lupin flour'],
        'molluscs': ['oyster', 'mussel', 'clam', 'scallop', 'squid', 'octopus']
    }
    
    # Add variations for matching ingredients
    for key, values in variations_dict.items():
        if key in clean_ing:
            variations.update(values)
    
    return variations

def map_allergens_to_ingredients(ingredients):
    """
    Map ingredients to potential allergies using the dataset
    
    Args:
        ingredients: List of ingredients or comma-separated string
    
    Returns:
        List of dictionaries containing ingredient and allergy information
    """
    if not ingredients:
        logger.warning("No ingredients provided to map_allergens_to_ingredients")
        return []

    # If ingredients is a string, split it into a list
    if isinstance(ingredients, str):
        ingredients = [ing.strip() for ing in ingredients.split(",") if ing.strip()]
        logger.info(f"Split ingredient string into list: {ingredients}")

    # Convert all ingredients to lowercase and clean
    ingredients_clean = [clean_ingredient(ing) for ing in ingredients]
    logger.info(f"Cleaned ingredients: {ingredients_clean}")
    
    # Dictionary to store matched allergies
    matched_allergies = {}
    
    # Log the allergies dataset
    logger.info(f"Using allergies dataset with {len(df_allergies)} entries")
    logger.info(f"Sample allergens: {', '.join(df_allergies['Ingredients'].head().tolist())}")
    
    # First pass: Direct matches
    direct_matches = df_allergies[
        df_allergies["Ingredients"].str.lower().isin([ing.lower() for ing in ingredients_clean])
    ]
    
    # Add direct matches to results
    for _, row in direct_matches.iterrows():
        key = row['Ingredients']
        problems = row.get('Allergies/Problems Caused', '')
        if key not in matched_allergies:
            matched_allergies[key] = {
                'Ingredients': row['Ingredients'],
                'Allergies': problems if not pd.isna(problems) else '',
                'Found_In': row['Ingredients'],
                'Confidence': 'High',
                'Action': 'Avoid' if 'severe' in str(problems).lower() or 'anaphylaxis' in str(problems).lower() else 'Caution'
            }
            logger.info(f"Direct match found: {key}")
    
    # Second pass: Check for variations and partial matches
    for ingredient in ingredients_clean:
        ingredient_variations = get_ingredient_variations(ingredient)
        logger.info(f"Checking variations for {ingredient}: {ingredient_variations}")
        
        for _, row in df_allergies.iterrows():
            allergen = clean_ingredient(str(row['Ingredients']))
            allergen_variations = get_ingredient_variations(allergen)
            problems = row.get('Allergies/Problems Caused', '')
            
            # More lenient matching: check if any part of the ingredient matches
            found_match = False
            match_type = None
            
            # Check for exact matches
            if ingredient in allergen_variations or allergen in ingredient_variations:
                found_match = True
                match_type = "exact"
            
            # Check for partial matches (if no exact match found)
            if not found_match:
                for variation in allergen_variations:
                    if variation in ingredient or ingredient in variation:
                        found_match = True
                        match_type = "partial"
                        break
                
                if not found_match:
                    for variation in ingredient_variations:
                        if variation in allergen or allergen in variation:
                            found_match = True
                            match_type = "partial"
                            break
            
            if found_match:
                key = row['Ingredients']
                if key not in matched_allergies:  # Only add if not already found
                    matched_allergies[key] = {
                        'Ingredients': row['Ingredients'],
                        'Allergies': problems if not pd.isna(problems) else '',
                        'Found_In': ingredient,
                        'Confidence': 'High' if match_type == "exact" else 'Medium',
                        'Action': 'Avoid' if 'severe' in str(problems).lower() or 'anaphylaxis' in str(problems).lower() else 'Caution'
                    }
                    logger.info(f"Found {match_type} match: {ingredient} -> {key}")
    
    # Convert dictionary to list and sort by Action (Avoid first) and Confidence
    result = list(matched_allergies.values())
    result.sort(key=lambda x: (x['Action'] != 'Avoid', x['Confidence'] != 'High'))
    
    logger.info(f"Found {len(result)} allergen matches")
    if result:
        logger.info(f"Sample matches: {result[:2]}")
    
    return result 