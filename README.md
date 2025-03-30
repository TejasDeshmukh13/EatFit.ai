# EatFit - Diet and Nutrition Helper

EatFit is a Flask-based web application that helps users analyze food product nutrition labels, get diet recommendations, and make healthier food choices.

## Project Structure

The application has been organized into a standard Flask project structure for better maintainability:

```
├── run.py                   # Script to run the application
└── src/                     # Main source code directory
    ├── app.py               # Main application entry point
    ├── requirements.txt     # Dependencies
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

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`
4. Install dependencies: `pip install -r src/requirements.txt`
5. Set up the database: `mysql -u root -p < src/database/setup_database.sql`
6. Run the application from the root directory: `python run.py`

## Features

- User authentication (signup, login, profile management)
- Health data tracking
- Diet plan recommendations based on user health data
- Food label OCR recognition
- Nutrition analysis and scoring
- Alternative product recommendations

## Technologies Used

- Flask - Web framework
- MySQL - Database
- PyTesseract - OCR engine
- OpenCV - Image processing
- Scikit-learn - Machine learning
- Bootstrap - Frontend styling

## Usage

1. Sign up or log in to the application
2. Fill out your health profile
3. Use the application to:
   - Scan food product labels
   - Get personalized diet recommendations
   - Track your nutrition
   - Find healthier alternative products 