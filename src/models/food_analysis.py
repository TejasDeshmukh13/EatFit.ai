from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import requests
import json

class ProcessingLevel(Enum):
    UNPROCESSED = 1
    MINIMALLY_PROCESSED = 2
    PROCESSED = 3
    ULTRA_PROCESSED = 4

class AdditiveCategory(Enum):
    PRESERVATIVE = "Preservative"
    COLORANT = "Colorant"
    EMULSIFIER = "Emulsifier"
    ANTIOXIDANT = "Antioxidant"
    STABILIZER = "Stabilizer"
    THICKENER = "Thickener"

@dataclass
class Additive:
    code: str
    name: str
    category: AdditiveCategory
    description: str
    concerns: List[str]
    vegan: bool = True
    processing_level: ProcessingLevel = ProcessingLevel.PROCESSED
    
@dataclass
class ProcessingMarker:
    name: str
    description: str
    level: ProcessingLevel

@dataclass
class IngredientAnalysis:
    name: str
    percentage: Optional[float] = None
    vegan: bool = True
    vegetarian: bool = True
    from_palm_oil: bool = False
    organic: bool = False
    allergen: bool = False

@dataclass
class ProductAnalysis:
    processing_level: ProcessingLevel
    processing_markers: List[str]
    additives: List[Additive]
    contains_palm_oil: bool
    is_vegan: bool
    nova_group: Optional[int]
    nutriscore_grade: Optional[str]
    ingredients_analysis: Optional[List[IngredientAnalysis]]
    allergens: Optional[List[str]]
    traces: Optional[List[str]]
    serving_size: Optional[str]
    product_name: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'product_name': self.product_name,
            'brand': self.brand,
            'image_url': self.image_url,
            'processing': {
                'level': self.processing_level.name,
                'markers': self.processing_markers,
                'nova_group': self.nova_group
            },
            'additives': [
                {
                    'code': a.code,
                    'name': a.name,
                    'description': a.description,
                    'vegan': a.vegan,
                    'processing_level': a.processing_level.name
                } for a in self.additives
            ],
            'ingredients': {
                'analysis': [
                    {
                        'name': i.name,
                        'percentage': i.percentage,
                        'vegan': i.vegan,
                        'vegetarian': i.vegetarian,
                        'from_palm_oil': i.from_palm_oil,
                        'organic': i.organic,
                        'allergen': i.allergen
                    } for i in (self.ingredients_analysis or [])
                ],
                'palm_oil': self.contains_palm_oil,
                'vegan': self.is_vegan,
                'allergens': self.allergens,
                'traces': self.traces,
                'serving_size': self.serving_size
            },
            'nutrition': {
                'nutriscore_grade': self.nutriscore_grade
            }
        }

# Database of common additives
ADDITIVES_DB = {
    "E322": Additive(
        code="E322",
        name="Lecithins",
        category=AdditiveCategory.EMULSIFIER,
        description="Natural or synthetic emulsifiers used to help mix ingredients that would normally separate",
        concerns=["May be derived from soy or eggs", "Generally recognized as safe"],
        vegan=False  # Can be non-vegan if derived from egg
    ),
    "E322i": Additive(
        code="E322i",
        name="Lecithin",
        category=AdditiveCategory.EMULSIFIER,
        description="Specific type of lecithin, commonly used as an emulsifier and stabilizer",
        concerns=["May be derived from soy or eggs", "Generally recognized as safe"],
        vegan=False  # Can be non-vegan if derived from egg
    )
}

# Database of processing markers
PROCESSING_MARKERS = {
    "hydrogenated_oils": ProcessingMarker(
        name="Hydrogenated Oils",
        description="Oils that have been chemically altered to be solid at room temperature",
        level=ProcessingLevel.ULTRA_PROCESSED
    ),
    "artificial_flavors": ProcessingMarker(
        name="Artificial Flavors",
        description="Synthetic flavor compounds",
        level=ProcessingLevel.ULTRA_PROCESSED
    ),
    "preservatives": ProcessingMarker(
        name="Preservatives",
        description="Chemical substances added to prevent spoilage",
        level=ProcessingLevel.PROCESSED
    )
}

def get_product_from_off(barcode: str) -> Optional[Dict]:
    """
    Fetch product data from Open Food Facts API.
    """
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url)
        data = response.json()
        
        if data.get('status') == 1:
            return data['product']
        return None
    except Exception as e:
        print(f"Error fetching from Open Food Facts: {e}")
        return None

def extract_additives_from_off(product_data: Dict) -> List[Dict]:
    """Extract additives information from Open Food Facts data."""
    additives = []
    
    # Get additives from various possible fields
    additive_tags = product_data.get('additives_tags', [])
    
    for tag in additive_tags:
        # Extract E-number from tag (e.g., 'en:e322' -> 'E322')
        code = tag.split(':')[-1].upper()
        if not code.startswith('E'):
            code = 'E' + code
            
        # Add to list with basic info
        additives.append({
            'code': code,
            'name': product_data.get('additives_original_tags', {}).get(code, code),
            'text': None  # Additional info can be added here if available
        })
    
    return additives

def analyze_ingredients_from_off(product_data: Dict) -> List[IngredientAnalysis]:
    """Extract detailed ingredient information from Open Food Facts data."""
    ingredients_analysis = []
    
    if 'ingredients' in product_data:
        for ing in product_data['ingredients']:
            # Extract ingredient information
            name = ing.get('text', '').lower()
            percentage = ing.get('percent_estimate', None)
            vegan = ing.get('vegan', 'yes') != 'no'
            vegetarian = ing.get('vegetarian', 'yes') != 'no'
            from_palm_oil = ing.get('from_palm_oil', '0') == '1'
            organic = ing.get('organic', '0') == '1'
            
            # Check if it's an allergen
            allergen = False
            if 'allergens' in product_data:
                allergen = name in [a.lower() for a in product_data.get('allergens_tags', [])]
            
            ingredients_analysis.append(IngredientAnalysis(
                name=name,
                percentage=percentage,
                vegan=vegan,
                vegetarian=vegetarian,
                from_palm_oil=from_palm_oil,
                organic=organic,
                allergen=allergen
            ))
    
    return ingredients_analysis

def analyze_product_with_off(barcode: str) -> Optional[ProductAnalysis]:
    """Analyze a food product using Open Food Facts data."""
    try:
        # Get product data from Open Food Facts
        product_data = get_product_from_off(barcode)
        if not product_data:
            print(f"No data found for barcode: {barcode}")
            return None

        # Initialize variables with safe defaults
        processing_markers = []
        additives = []
        contains_palm_oil = False
        is_vegan = True
        max_processing_level = ProcessingLevel.UNPROCESSED
        ingredients_analysis = []
        allergens = []
        traces = []
        serving_size = None
        nova_group = None
        nutriscore_grade = None

        # Get basic product info (with safe defaults)
        product_name = product_data.get('product_name', f"Product {barcode}")
        brand = product_data.get('brands', 'Unknown Brand')
        image_url = product_data.get('image_url')

        # Get NOVA group and processing level
        nova_group = product_data.get('nova_group')
        if nova_group:
            if nova_group == 4:
                max_processing_level = ProcessingLevel.ULTRA_PROCESSED
            elif nova_group == 3:
                max_processing_level = ProcessingLevel.PROCESSED
            elif nova_group == 2:
                max_processing_level = ProcessingLevel.MINIMALLY_PROCESSED

        # Get Nutri-Score
        if 'nutriscore_grade' in product_data:
            nutriscore_grade = product_data.get('nutriscore_grade', '').upper()

        # Analyze ingredients
        try:
            ingredients = product_data.get('ingredients', [])
            if ingredients and isinstance(ingredients, list):
                for ing in ingredients:
                    if isinstance(ing, dict):
                        name = ing.get('text', '')
                        if name:
                            analysis = IngredientAnalysis(
                                name=name,
                                percentage=ing.get('percent'),
                                vegan='vegan' in ing.get('vegan', '').lower(),
                                vegetarian='vegetarian' in ing.get('vegetarian', '').lower(),
                                from_palm_oil=ing.get('from_palm_oil', False),
                                organic=ing.get('organic', False),
                                allergen=ing.get('allergen', False)
                            )
                            ingredients_analysis.append(analysis)
        except Exception as e:
            print(f"Error analyzing ingredients: {str(e)}")

        # Check palm oil
        try:
            contains_palm_oil = (
                product_data.get('ingredients_from_palm_oil_n', 0) > 0 or
                product_data.get('ingredients_that_may_be_from_palm_oil_n', 0) > 0
            )
        except Exception as e:
            print(f"Error checking palm oil: {str(e)}")

        # Check vegan status
        try:
            if 'ingredients_analysis_tags' in product_data:
                ingredients_tags = product_data.get('ingredients_analysis_tags', [])
                if isinstance(ingredients_tags, list):
                    is_vegan = 'en:non-vegan' not in ingredients_tags
        except Exception as e:
            print(f"Error checking vegan status: {str(e)}")

        # Get allergens and traces
        try:
            allergens_tags = product_data.get('allergens_tags', [])
            if isinstance(allergens_tags, list):
                allergens = [
                    allergen.split(':')[-1].replace('-', ' ').title()
                    for allergen in allergens_tags
                ]
                
            traces_tags = product_data.get('traces_tags', [])
            if isinstance(traces_tags, list):
                traces = [
                    trace.split(':')[-1].replace('-', ' ').title()
                    for trace in traces_tags
                ]
        except Exception as e:
            print(f"Error parsing allergens/traces: {str(e)}")

        # Get serving size
        serving_size = product_data.get('serving_size')

        # Process additives
        try:
            additive_tags = product_data.get('additives_tags', [])
            if isinstance(additive_tags, list):
                for tag in additive_tags:
                    try:
                        code = tag.split(':')[-1].upper()
                        if not code.startswith('E'):
                            code = 'E' + code
                        
                        name = product_data.get('additives_original_tags', {}).get(code, code)
                        description = product_data.get('additives_debug_tags', {}).get(code, '')
                        
                        additive = Additive(
                            code=code,
                            name=name,
                            description=description
                        )
                        additives.append(additive)
                    except Exception as additive_err:
                        print(f"Error processing additive {tag}: {str(additive_err)}")
        except Exception as e:
            print(f"Error processing additives: {str(e)}")

        # Create and return the product analysis
        return ProductAnalysis(
            processing_level=max_processing_level,
            processing_markers=processing_markers,
            additives=additives,
            contains_palm_oil=contains_palm_oil,
            is_vegan=is_vegan,
            nova_group=nova_group,
            nutriscore_grade=nutriscore_grade,
            ingredients_analysis=ingredients_analysis,
            allergens=allergens,
            traces=traces,
            serving_size=serving_size,
            product_name=product_name,
            brand=brand,
            image_url=image_url
        )
    except Exception as e:
        print(f"Error analyzing product: {str(e)}")
        return None

def format_analysis_results(analysis: Dict) -> str:
    """Format the analysis results into a human-readable string."""
    result = []
    
    # Food Processing section
    result.append("Product Analysis Results\n")
    
    # Product name if available
    if analysis.get('product_name'):
        result.append(f"Product: {analysis['product_name']}")
    
    # Processing info
    result.append("\nFood Processing")
    if analysis.get('nova_group'):
        result.append(f"NOVA Group: {analysis['nova_group']}")
    else:
        result.append("Processing information not available")
    
    # Additives section
    result.append("\nAdditives")
    if analysis.get('additives'):
        for additive in analysis['additives']:
            result.append(f"{additive['code']} - {additive['name']}")
            if additive.get('text'):
                result.append(f"Details: {additive['text']}")
    else:
        result.append("No additives information available")
    
    # Ingredients Analysis section
    result.append("\nIngredients Analysis")
    
    ingredients_info = []
    
    # Palm oil check
    if analysis.get('ingredients_from_palm_oil_n') is not None:
        if analysis['ingredients_from_palm_oil_n'] > 0:
            palm_oil_ingredients = analysis.get('ingredients_from_palm_oil_tags', [])
            ingredients_info.append(f"🌴 Contains palm oil" + 
                                 (f" in: {', '.join(palm_oil_ingredients)}" if palm_oil_ingredients else ""))
        elif analysis.get('ingredients_that_may_be_from_palm_oil_n', 0) > 0:
            ingredients_info.append("🌴 May contain palm oil")
    
    # Vegan/Vegetarian status
    if 'ingredients_analysis_tags' in analysis:
        if 'en:non-vegan' in analysis['ingredients_analysis_tags']:
            ingredients_info.append("🥩 Non-vegan")
        elif 'en:vegan' in analysis['ingredients_analysis_tags']:
            ingredients_info.append("🌱 Vegan")
        
        if 'en:non-vegetarian' in analysis['ingredients_analysis_tags']:
            ingredients_info.append("🥩 Non-vegetarian")
        elif 'en:vegetarian' in analysis['ingredients_analysis_tags']:
            ingredients_info.append("🌱 Vegetarian")
    
    # Allergens
    if analysis.get('allergens_tags'):
        allergens = [allergen.split(':')[-1].replace('-', ' ').title() 
                    for allergen in analysis['allergens_tags']]
        ingredients_info.append(f"⚠️ Contains allergens: {', '.join(allergens)}")
    
    # Traces
    if analysis.get('traces_tags'):
        traces = [trace.split(':')[-1].replace('-', ' ').title() 
                 for trace in analysis['traces_tags']]
        ingredients_info.append(f"⚠️ May contain traces of: {', '.join(traces)}")
    
    if ingredients_info:
        result.extend(ingredients_info)
    else:
        result.append("No detailed ingredients analysis available")
    
    return "\n".join(result) 