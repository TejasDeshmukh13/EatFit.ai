import joblib
import os
import numpy as np

# Get the path to the project root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

print(f"Looking for model files in: {project_root}")

try:
    # Load the encoders
    label_encoders_path = os.path.join(project_root, "label_encoders.pkl")
    print(f"Loading label encoders from: {label_encoders_path}")
    label_encoders = joblib.load(label_encoders_path)
    
    # Print information about the encoders
    print("\n== Label Encoders ==")
    for key, encoder in label_encoders.items():
        print(f"\nEncoder: {key}")
        print(f"Classes: {encoder.classes_}")
        print(f"Number of classes: {len(encoder.classes_)}")
    
    # Load one of the models to test predictions
    rf_breakfast_path = os.path.join(project_root, "rf_breakfast.pkl")
    print(f"\nLoading breakfast model from: {rf_breakfast_path}")
    rf_breakfast = joblib.load(rf_breakfast_path)
    
    # Print model info
    print("\n== Model Information ==")
    print(f"Model type: {type(rf_breakfast)}")
    
    # Test predictions for different diseases
    print("\n== Test Predictions ==")
    diseases = ['None', 'Diabetes', 'Hypertension', 'Heart disease']
    
    for disease in diseases:
        # Encode the disease
        if disease == 'None':
            disease_encoded = 0
        elif disease.capitalize() in label_encoders["Diseases"].classes_:
            disease_encoded = label_encoders["Diseases"].transform([disease.capitalize()])[0]
        else:
            print(f"Disease '{disease}' not found in model classes")
            continue
            
        # Create test data
        age = 40
        weight = 70
        height_m = 1.75
        bmi = weight / (height_m ** 2)
        
        # Create the input data array
        user_data = np.array([[age, weight, height_m, bmi, disease_encoded]])
        
        # Make prediction
        breakfast_pred = rf_breakfast.predict(user_data)[0]
        breakfast = label_encoders["Breakfast"].inverse_transform([breakfast_pred])[0]
        
        print(f"\nDisease: {disease} (encoded: {disease_encoded})")
        print(f"Breakfast prediction: {breakfast}")
        
except Exception as e:
    print(f"Error: {e}") 