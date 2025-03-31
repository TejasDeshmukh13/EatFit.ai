"""
Image processing utilities for OCR.
"""
import os
import cv2
import pytesseract
import re
import numpy as np
import time

# OCR Configuration
OCR_CONFIGS = [
    # Config 1: Optimized specifically for nutrition labels with columnar data
    {
        'oem': 1,  # Legacy engine (sometimes more accurate for tabular data)
        'psm': 4,  # Assume single column of text with variable sizes
        'extra': '--tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata" -l eng --dpi 300'
    },
    
    # Config 2: LSTM neural network with single column assumption
    {
        'oem': 3,  # LSTM neural net only
        'psm': 6,  # Assume a single uniform block of text
        'extra': '-c tessedit_char_whitelist="0123456789.,ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz() " --tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata" -l eng'
    },
    
    # Config 3: Optimized for numerical values and measurements
    {
        'oem': 3,
        'psm': 11,  # Sparse text with OSD
        'extra': '-c tessedit_char_whitelist="0123456789.,g% " --tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata" -l eng'
    },
    
    # Config 4: High accuracy mode for structured text
    {
        'oem': 1,
        'psm': 3,  # Fully automatic page segmentation
        'extra': '--tessdata-dir "C:\\Program Files\\Tesseract-OCR\\tessdata" -l eng'
    }
]

def enhance_image(image):
    """
    Enhanced image processing specifically for Indian nutrition labels
    """
    # Make a copy to avoid modifying the original
    img = image.copy()
    
    # Resize if image is too small
    height, width = img.shape[:2]
    if width < 800 or height < 600:
        scale_factor = max(800 / width, 600 / height)
        img = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    
    # Try multiple preprocessing techniques to increase OCR accuracy
    processed_images = []
    
    # 1. Basic grayscale conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    processed_images.append(gray)
    
    # 2. Bilateral filter to preserve edges while removing noise
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)
    processed_images.append(blurred)
    
    # 3. Apply CLAHE for better contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(blurred)
    processed_images.append(enhanced)
    
    # 4. Apply adaptive thresholding
    binary_adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    processed_images.append(binary_adaptive)
    
    # 5. Apply Otsu thresholding
    _, binary_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(binary_otsu)
    
    # 6. Apply morphological operations to both thresholded images
    for binary in [binary_adaptive, binary_otsu]:
        # Noise removal (opening)
        kernel = np.ones((2, 2), np.uint8)
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        processed_images.append(opening)
        
        # Connect text (closing)
        kernel = np.ones((2, 2), np.uint8)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
        processed_images.append(closing)
    
    # 7. Apply edge enhancement
    edges = cv2.Canny(enhanced, 50, 150)
    dilated_edges = cv2.dilate(edges, np.ones((2,2), np.uint8), iterations=1)
    edge_enhanced = cv2.bitwise_not(dilated_edges)
    processed_images.append(edge_enhanced)
    
    # Save debug images
    debug_dir = os.path.join('debug_images')
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    timestamp = int(time.time())
    for i, img in enumerate(processed_images):
        cv2.imwrite(f"{debug_dir}/process_{i}_{timestamp}.jpg", img)
    
    return processed_images

def find_nutrition_values(text):
    """
    Extract nutrition values from OCR text using regex patterns tailored for nutrition labels,
    with special attention to Indian nutrition label formats
    """
    # Extended patterns for better matching of Indian nutrition labels
    patterns = {
        'energy_kcal': r'(?:energy|calories|kcal|energy value)[^\d]*(\d+[\.,]?\d*)\s*(?:kcal|kj)?',
        'fat': r'(?:total\s*fat|fat\s*content|fat)[^\d]*(\d+[\.,]?\d*)\s*g',
        'saturated_fat': r'(?:saturated\s*fat|saturates|sat\.\s*fat)[^\d]*(\d+[\.,]?\d*)\s*g',
        'carbohydrates': r'(?:total\s*carbohydrate|carbohydrate|carbohydrates|carb|carbs)[^\d]*(\d+[\.,]?\d*)\s*g',
        'sugars': r'(?:of\s*which\s*sugars|sugars?|total\s*sugars)[^\d]*(\d+[\.,]?\d*)\s*g',
        'fiber': r'(?:dietary\s*fibre|dietary\s*fiber|fibre|fiber)[^\d]*(\d+[\.,]?\d*)\s*g',
        'protein': r'(?:protein|proteins)[^\d]*(\d+[\.,]?\d*)\s*g',
        'salt': r'(?:salt|sodium)[^\d]*(\d+[\.,]?\d*)\s*(?:g|mg)'
    }
    
    results = {}
    text = text.lower()
    
    # Print the text for debugging
    print("OCR Text for analysis:")
    print(text)
    
    for nutrient, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            try:
                # Handle potential comma as decimal separator
                value_text = match.group(1).replace(',', '.')
                value = float(value_text)
                
                # Special case for salt/sodium conversion
                if nutrient == 'salt' and 'mg' in match.group(0):
                    value = value / 1000  # Convert mg to g
                
                results[nutrient] = value
                print(f"Found {nutrient}: {value}")
            except (ValueError, IndexError) as e:
                print(f"Error parsing {nutrient}: {e}")
                continue
    
    return results

def enhanced_ocr(processed_images):
    """
    Perform OCR with multiple configurations and images for best results.
    """
    all_results = {}
    
    for i, img in enumerate(processed_images):
        for cfg_idx, cfg in enumerate(OCR_CONFIGS):
            try:
                config_str = '--oem 3 --psm 6 -c tessedit_char_whitelist="0123456789.,ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz() " --tessdata-dir "D:\\PyProject\\Eatfit\\Tesseract\\tessdata" -l eng'
                text = pytesseract.image_to_string(img, config=config_str)
                
                # Clean OCR text
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Extract nutrition values
                values = find_nutrition_values(text)
                
                # Merge with existing results
                for key, value in values.items():
                    if key not in all_results or (key in all_results and value > 0):
                        all_results[key] = value
                        
                # Debug log
                with open("ocr_debug.log", "a") as f:
                    f.write(f"Config {cfg_idx+1}, Image {i+1}:\n{text}\n\nExtracted: {values}\n\n")
                    
            except Exception as e:
                print(f"OCR Error (Config {cfg_idx+1}, Image {i+1}): {str(e)}")
    
    return all_results

def extract_text(image_path):
    """
    Extract text from an image and process it to find nutrition information.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at {image_path}")
            
        processed_images = enhance_image(img)
        nutrition_data = enhanced_ocr(processed_images)
        
        print(f"Extracted nutrition data: {nutrition_data}")
        return nutrition_data
        
    except Exception as e:
        print(f"Extract Text Error: {str(e)}")
        return {} 