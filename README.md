# 🥗 EatFit - Diet & Nutrition Helper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

EatFit is a comprehensive Flask-based web application designed to help users make healthier food choices through nutrition label analysis, personalized diet plans, and smart product recommendations.

![EatFit Banner](https://via.placeholder.com/800x200?text=EatFit+Diet+and+Nutrition+Helper)

## ✨ Features

- 🔐 **User Authentication** - Secure signup, login and profile management
- 📊 **Health Tracking** - Monitor your key health metrics over time
- 🍽️ **Diet Recommendations** - AI-powered personalized meal planning
- 📱 **Food Label Scanner** - OCR-based nutrition label recognition
- 🧮 **Nutrition Analysis** - Detailed breakdown and health scoring
- 🔄 **Alternative Products** - Find healthier options for your favorite foods

## 📋 Table of Contents

- [🥗 EatFit - Diet \& Nutrition Helper](#-eatfit---diet--nutrition-helper)
  - [✨ Features](#-features)
  - [📋 Table of Contents](#-table-of-contents)
  - [📁 Project Structure](#-project-structure)
  - [🚀 Installation](#-installation)
  - [📖 Usage Guide](#-usage-guide)
  - [💻 Technologies](#-technologies)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)

## 📁 Project Structure

```
├── run.py                   # Application entry point
└── src/                     # Main source code directory
    ├── app.py               # Flask application setup
    ├── requirements.txt     # Project dependencies
    ├── config/              # Configuration files
    │   ├── __init__.py
    │   └── database.py      # Database configuration
    ├── database/            # Database related files
    │   ├── __init__.py
    │   ├── db.py            # Database connection handler
    │   └── setup_database.sql # SQL schema setup
    ├── models/              # ML models and related code
    │   ├── __init__.py
    │   ├── diet_plan.py     # Diet recommendation model
    │   ├── train_model.py   # Model training script
    │   ├── rf_breakfast.pkl # Breakfast model
    │   ├── rf_lunch.pkl     # Lunch model
    │   ├── rf_dinner.pkl    # Dinner model
    │   └── label_encoders.pkl # Label encoders for models
    ├── routes/              # Route handlers
    │   ├── __init__.py
    │   ├── auth_routes.py   # Authentication routes
    │   ├── user_routes.py   # User profile routes
    │   ├── product_routes.py # Product analysis routes
    │   └── diet_routes.py   # Diet plan routes
    ├── static/              # Static assets
    │   ├── css/             # CSS files
    │   ├── js/              # JavaScript files
    │   ├── images/          # Image files
    │   └── uploads/         # User uploads
    ├── templates/           # HTML templates
    │   ├── login.html
    │   ├── signup.html
    │   ├── profile.html
    │   └── ...
    ├── utils/               # Utility functions
    │   ├── __init__.py
    │   ├── common.py        # Common utility functions
    │   ├── image_processing.py # Image processing utilities
    │   └── nutrition.py     # Nutrition analysis utilities
    └── data/                # Data files
        └── EATFIT_DIET.csv  # Diet dataset
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

1. **Sign up or log in** to access your personalized dashboard
2. **Complete your health profile** to receive tailored recommendations
3. **Scan product labels** using your device's camera or upload images
4. **View nutrition analysis** with detailed breakdown and health scores
5. **Get diet recommendations** based on your health goals and preferences
6. **Discover alternatives** to make healthier food choices

## 💻 Technologies

- **[Flask](https://flask.palletsprojects.com/)** - Web framework
- **[MySQL](https://www.mysql.com/)** - Database management
- **[PyTesseract](https://github.com/madmaze/pytesseract)** - OCR engine
- **[OpenCV](https://opencv.org/)** - Image processing
- **[Scikit-learn](https://scikit-learn.org/)** - Machine learning
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