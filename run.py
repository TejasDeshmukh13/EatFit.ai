import os
import sys

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the app from src
from src.app import app

if __name__ == '__main__':
    # Ensure the upload directories exist
    os.makedirs(os.path.join('src', 'static', 'uploads'), exist_ok=True)
    os.makedirs(os.path.join('src', 'static', 'images'), exist_ok=True)
    
    # Run the app
    app.run(debug=True, port=5001) 