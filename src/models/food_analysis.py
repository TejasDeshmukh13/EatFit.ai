from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import requests

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

# Known additives database with descriptions
ADDITIVES_INFO = {
    "E100": "Curcumin - Yellow-orange coloring from turmeric",
    "E101": "Riboflavin - Yellow coloring (Vitamin B2)",
    "E102": "Tartrazine - Yellow synthetic dye",
    "E104": "Quinoline Yellow - Yellow synthetic dye",
    "E120": "Cochineal - Red coloring from insects",
    "E122": "Azorubine - Red synthetic coloring",
    "E129": "Allura Red AC - Red synthetic coloring",
    "E131": "Patent Blue V - Blue synthetic coloring",
    "E140": "Chlorophylls - Green pigment from plants",
    "E141": "Copper complexes of chlorophylls - Green coloring",
    "E150a": "Plain caramel - Brown coloring",
    "E160a": "Alpha-carotene - Orange coloring",
    "E160c": "Paprika extract - Red coloring from peppers",
    "E162": "Beetroot Red - Natural red coloring",
    "E170": "Calcium carbonate - White mineral",
    "E200": "Sorbic acid - Preservative",
    "E202": "Potassium sorbate - Preservative",
    "E210": "Benzoic acid - Preservative",
    "E211": "Sodium benzoate - Preservative",
    "E212": "Potassium benzoate - Preservative",
    "E220": "Sulphur dioxide - Preservative/antioxidant",
    "E221": "Sodium sulphite - Preservative",
    "E223": "Sodium metabisulphite - Preservative/antioxidant",
    "E224": "Potassium metabisulphite - Preservative/antioxidant",
    "E250": "Sodium nitrite - Preservative (cured meats)",
    "E251": "Sodium nitrate - Preservative (cured meats)",
    "E260": "Acetic acid - Preservative (vinegar)",
    "E270": "Lactic acid - Acidity regulator",
    "E280": "Propionic acid - Preservative (bread)",
    "E290": "Carbon dioxide - Packaging gas",
    "E296": "Malic acid - Acidity regulator/flavor enhancer",
    "E297": "Fumaric acid - Acidity regulator",
    "E300": "Ascorbic acid - Antioxidant (Vitamin C)",
    "E301": "Sodium ascorbate - Antioxidant",
    "E306": "Tocopherol-rich extract - Antioxidant (Vitamin E)",
    "E307": "Alpha-tocopherol - Antioxidant (Vitamin E)",
    "E322": "Lecithins - Emulsifier (from soy or eggs)",
    "E325": "Sodium lactate - Antioxidant/humectant",
    "E330": "Citric acid - Acidity regulator/antioxidant",
    "E331": "Sodium citrates - Acidity regulator/emulsifier",
    "E332": "Potassium citrates - Acidity regulator",
    "E333": "Calcium citrates - Acidity regulator/firming agent",
    "E334": "Tartaric acid - Acidity regulator",
    "E335": "Sodium tartrates - Acidity regulator/stabilizer",
    "E336": "Potassium tartrates - Stabilizer/sequestrant",
    "E340": "Potassium phosphates - Acidity regulator/stabilizer",
    "E350": "Sodium malates - Acidity regulator",
    "E375": "Niacin - Vitamin B3",
    "E392": "Rosemary extracts - Antioxidant",
    "E400": "Alginic acid - Thickener/stabilizer",
    "E401": "Sodium alginate - Thickener/stabilizer",
    "E406": "Agar - Thickener/gelling agent",
    "E407": "Carrageenan - Thickener/stabilizer",
    "E407a": "Processed eucheuma seaweed - Thickener",
    "E410": "Locust bean gum - Thickener/stabilizer",
    "E412": "Guar gum - Thickener/stabilizer",
    "E413": "Tragacanth - Thickener/stabilizer",
    "E414": "Acacia gum - Thickener/stabilizer",
    "E415": "Xanthan gum - Thickener/stabilizer",
    "E422": "Glycerol - Humectant/sweetener",
    "E440": "Pectins - Gelling agent/thickener",
    "E441": "Gelatine - Gelling agent",
    "E450": "Diphosphates - Emulsifier/stabilizer",
    "E460": "Cellulose - Anti-caking agent/emulsifier",
    "E461": "Methyl cellulose - Thickener/emulsifier",
    "E464": "Hydroxypropyl methyl cellulose - Thickener/emulsifier",
    "E471": "Mono- and diglycerides of fatty acids - Emulsifier",
    "E472e": "Mono- and diacetyl tartaric acid esters - Emulsifier",
    "E476": "Polyglycerol polyricinoleate - Emulsifier (chocolate)",
    "E481": "Sodium stearoyl-2-lactylate - Emulsifier",
    "E500": "Sodium carbonates - Acidity regulator/raising agent",
    "E501": "Potassium carbonates - Acidity regulator/stabilizer",
    "E503": "Ammonium carbonates - Raising agent",
    "E504": "Magnesium carbonates - Anti-caking agent",
    "E570": "Fatty acids - Anti-caking agent/foam stabilizer",
    "E621": "Monosodium glutamate - Flavor enhancer (MSG)",
    "E631": "Sodium inosinate - Flavor enhancer",
    "E901": "Beeswax - Glazing agent",
    "E903": "Carnauba wax - Glazing agent",
    "E950": "Acesulfame K - Artificial sweetener",
    "E951": "Aspartame - Artificial sweetener",
    "E953": "Isomalt - Sugar substitute/sweetener",
    "E954": "Saccharin - Artificial sweetener",
    "E955": "Sucralose - Artificial sweetener",
    "E960": "Steviol glycosides - Natural sweetener (stevia)",
    "E965": "Maltitol - Sweetener/stabilizer",
    "E1442": "Hydroxy propyl distarch phosphate - Modified starch"
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

def get_product_from_off(barcode):
    """
    Get product information from the Open Food Facts API.
    This function is the primary method for fetching product data.
    
    Args:
        barcode (str): The product barcode to fetch
        
    Returns:
        dict: Dictionary containing product data or None if not found
    """
    try:
        if not barcode or len(barcode) < 8:
            return None
            
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if data.get('status') != 1 or 'product' not in data:
            return None
            
        product = data['product']
        
        # Process additives more comprehensively
        if 'additives_tags' in product:
            # Format additives to include proper E-codes with names and descriptions
            formatted_additives = []
            for tag in product['additives_tags']:
                # Extract the additive code from the tag
                code = tag.split(':')[-1]
                
                # Format properly for display
                if code.startswith('e'):
                    display_code = 'E' + code[1:]
                elif not code.startswith('E'):
                    display_code = 'E' + code
                else:
                    display_code = code
                
                # Try to get the name from additives_n field or original tags
                name = None
                if 'additives_original_tags' in product:
                    for original in product['additives_original_tags']:
                        if code in original.lower():
                            parts = original.split(':')
                            if len(parts) > 1:
                                name = parts[-1].replace('-', ' ').title()
                                break
                
                # If we didn't find a name, check additives_old_tags
                if not name and 'additives_old_tags' in product:
                    for old in product['additives_old_tags']:
                        if code in old.lower():
                            parts = old.split(':')
                            if len(parts) > 1:
                                name = parts[-1].replace('-', ' ').title()
                                break
                
                # If still no name, use the display code
                if not name:
                    name = display_code
                
                # Check our additives database for detailed description
                if display_code in ADDITIVES_INFO:
                    formatted_additives.append(ADDITIVES_INFO[display_code])
                else:
                    # Add to formatted list
                    formatted_additives.append(f"{display_code} - {name}")
            
            # Replace the original additives_tags with our better formatted version
            product['additives_tags'] = formatted_additives
        else:
            # Initialize as empty list if not present
            product['additives_tags'] = []
            
        # Process ingredients analysis tags
        if 'ingredients_analysis_tags' in product:
            # Clean up the tags for template use
            cleaned_tags = []
            for tag in product['ingredients_analysis_tags']:
                # Keep the original format for template conditionals
                cleaned_tags.append(tag.lower())
            product['ingredients_analysis_tags'] = cleaned_tags
        else:
            # Initialize as empty list if not present
            product['ingredients_analysis_tags'] = []
            
        return product
        
    except Exception as e:
        print(f"Error fetching product from OpenFoodFacts: {str(e)}")
        return None

def analyze_product_with_off(barcode):
    """
    Analyze a product using the Open Food Facts database.
    This is the primary function for analyzing food products.
    
    Args:
        barcode (str): The product barcode to analyze
        
    Returns:
        ProductAnalysis: An object containing the analysis results or None if failed
    """
    try:
        # Get product information from Open Food Facts API
        product = get_product_from_off(barcode)
        
        if not product:
            return None
            
        # Initialize with safe defaults
        nova_group = product.get('nova_group')
        if nova_group is None:
            nova_group = 4  # Default to ultra-processed if not specified
            
        if not isinstance(nova_group, int):
            try:
                nova_group = int(nova_group)
            except (ValueError, TypeError):
                nova_group = 4
                
        # Get product name and brand
        product_name = product.get('product_name', 'Unknown product')
        brand = product.get('brands', 'Unknown brand')
        image_url = product.get('image_url')
        
        # Get additives
        additives = []
        additives_tags = product.get('additives_tags', [])
        
        for additive_code in additives_tags:
            code = additive_code.upper().strip() if isinstance(additive_code, str) else str(additive_code)
            
            # Skip if not a valid additive code
            if not code.startswith('E'):
                continue
                
            # Try to find in our database
            if code in ADDITIVES_DB:
                additives.append(ADDITIVES_DB[code])
            else:
                # Create a basic additive object for unknown additives
                additives.append(
                    Additive(
                        code=code,
                        name=code,
                        category=AdditiveCategory.PRESERVATIVE,  # Default category
                        description=f"Additive {code}",
                        concerns=[],
                        vegan=True,  # Assume vegan by default
                        processing_level=ProcessingLevel.PROCESSED
                    )
                )
                
        # Determine processing level
        if nova_group == 1:
            processing_level = ProcessingLevel.UNPROCESSED
        elif nova_group == 2:
            processing_level = ProcessingLevel.MINIMALLY_PROCESSED
        elif nova_group == 3:
            processing_level = ProcessingLevel.PROCESSED
        else:  # nova_group == 4 or unknown
            processing_level = ProcessingLevel.ULTRA_PROCESSED
            
        # Determine processing markers
        processing_markers = []
        if additives:
            processing_markers.append("Contains additives")
        if processing_level == ProcessingLevel.ULTRA_PROCESSED:
            processing_markers.append("Ultra-processed food")
            
        # Check for palm oil
        contains_palm_oil = False
        if 'ingredients_from_palm_oil_n' in product:
            try:
                palm_oil_count = int(product['ingredients_from_palm_oil_n'])
                contains_palm_oil = palm_oil_count > 0
            except (ValueError, TypeError):
                contains_palm_oil = False
                
        # Determine vegan status
        is_vegan = True
        if 'vegan' in product:
            is_vegan = product['vegan'] not in ('no', 'non-vegan')
            
        # Get allergens and traces
        allergens = product.get('allergens_tags', [])
        allergens = [allergen.split(':')[-1] for allergen in allergens if ':' in allergen]
        
        traces = product.get('traces_tags', [])
        traces = [trace.split(':')[-1] for trace in traces if ':' in trace]
        
        # Get nutriscore grade
        nutriscore_grade = product.get('nutriscore_grade', '?')
        
        # Get serving size
        serving_size = product.get('serving_size', '')
        
        # Create and return product analysis
        analysis = ProductAnalysis(
            processing_level=processing_level,
            processing_markers=processing_markers,
            additives=additives,
            contains_palm_oil=contains_palm_oil,
            is_vegan=is_vegan,
            nova_group=nova_group,
            nutriscore_grade=nutriscore_grade,
            ingredients_analysis=None,  # Not implemented in this version
            allergens=allergens,
            traces=traces,
            serving_size=serving_size,
            product_name=product_name,
            brand=brand,
            image_url=image_url
        )
        
        return analysis
        
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