"""
Common utility functions used across the application.
"""

def allowed_file(filename):
    """
    Check if the file extension is allowed.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 