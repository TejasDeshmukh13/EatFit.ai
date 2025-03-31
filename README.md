# 🍽️ EatFit.ai - Food Review & Nutrition Helper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

EatFit is a comprehensive Flask-based web application designed to help users analyze and review food products, compare nutrition quality, and make healthier food choices.

## ✨ Key Features

- 🔍 **Food Product Analysis** - Scan barcodes to get detailed product information
- 🏷️ **Nutrition Label Scanner** - OCR-based nutrition label recognition  
- 🧪 **Additives & Ingredients Analysis** - Identify concerning additives and ingredients
- 🔢 **NOVA Score & Food Processing** - Understand how processed your food is
- ⚠️ **Allergen Detection** - Identify potential allergens in food products
- 🥗 **Healthier Alternatives** - Discover better options for your favorite foods
- 🥦 **Personalized Diet Plans** - Get AI-powered meal recommendations
- 🧮 **BMI & Health Tracking** - Monitor your health metrics

## 📸 App Screenshots

<p><strong>Food Product Analysis & Barcode Scanning</strong></p>
  
<p><strong>Alternative Product Recommendations</strong></p>
  
<p><strong>Personalized Diet Plans</strong></p>

## 📋 Table of Contents

- [🍽️ EatFit - Food Review \& Nutrition Helper](#️-eatfit---food-review--nutrition-helper)
  - [✨ Key Features](#-key-features)
  - [📸 App Screenshots](#-app-screenshots)
  - [📋 Table of Contents](#-table-of-contents)
  - [🔎 How Food Review Works](#-how-food-review-works)
  - [📁 Project Structure](#-project-structure)
  - [🚀 Installation](#-installation)
  - [📖 Usage Guide](#-usage-guide)
  - [💻 Technologies](#-technologies)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)

## 🔎 How Food Review Works

EatFit's food review system provides detailed analysis of food products through several components:

1. **Barcode Scanning** - Enter a product barcode to retrieve data from the Open Food Facts API
2. **Nutri-Score Analysis** - A-E grading system based on nutritional quality
3. **NOVA Classification** - Evaluates food processing level from 1 (unprocessed) to 4 (ultra-processed)
4. **Additives Analysis** - Identifies and explains food additives and their potential concerns
5. **Ingredients Analysis** - Highlights ingredients like palm oil and evaluates vegan/vegetarian status
6. **Allergen Detection** - Identifies common allergens and possible traces
7. **Health Analysis** - Personalized evaluation based on user health profiles
8. **Alternative Products** - Suggests healthier alternatives in the same category

## 📁 Project Structure

```
├── run.py                   # Application entry point
└── src/                     # Main source code directory
    ├── app.py               # Flask application setup
    ├── requirements.txt     # Project dependencies
    ├── models/              # Analysis models and related code
    │   ├── food_analysis.py # Food review and analysis logic
    │   └── diet_plan.py     # Diet recommendation model
    ├── routes/              # Route handlers
    │   ├── auth_routes.py   # Authentication routes
    │   ├── user_routes.py   # User profile routes
    │   ├── product_routes.py # Product analysis routes
    │   └── diet_routes.py   # Diet plan routes
    ├── utils/               # Utility functions
    │   ├── nutrition.py     # Nutrition analysis utilities
    │   ├── allergies.py     # Allergen detection utilities
    │   └── image_processing.py # OCR processing
    ├── templates/           # HTML templates
    │   ├── product_details.html # Food review display
    │   └── ...
    └── static/              # Static assets
        ├── images/          # Image assets
        └── uploads/         # User uploads
```

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/eatfit.git
   cd eatfit
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r src/requirements.txt
   ```

5. **Set up the database**
   ```bash
   mysql -u root -p < src/database/setup_database.sql
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

## 📖 Usage Guide

1. **Create an account or log in** to access all features
2. **Scan a product barcode** or enter it manually
3. **View the food review** with detailed information about:
   - Nutritional quality (Nutri-Score)
   - Processing level (NOVA classification)
   - Additives and their descriptions
   - Ingredient analysis
   - Allergen warnings
4. **Check for healthier alternatives** to make better food choices
5. **Complete your health profile** to receive personalized recommendations
6. **Get diet suggestions** based on your health metrics and goals

## 💻 Technologies

- **[Flask](https://flask.palletsprojects.com/)** - Web framework
- **[MySQL](https://www.mysql.com/)** - Database management
- **[Open Food Facts API](https://world.openfoodfacts.org/data)** - Food product database
- **[PyTesseract](https://github.com/madmaze/pytesseract)** - OCR engine for label scanning
- **[OpenCV](https://opencv.org/)** - Image processing
- **[Scikit-learn](https://scikit-learn.org/)** - Machine learning for diet recommendations
- **[Bootstrap](https://getbootstrap.com/)** - Frontend styling

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<p align="center">Made with ❤️ by the EatFit Team</p> 
