from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
import os
from utils.common import allowed_file

user_bp = Blueprint('user', __name__)

@user_bp.route('/health_form')
def health_form():
    if 'user_id' not in session:
        flash('Please log in to access the health form.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('healthForm.html')

@user_bp.route('/edit_health_data')
def edit_health_data_form():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    mysql = g.mysql
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM health_data WHERE user_id = %s", (user_id,))
    health_data = cur.fetchone()
    cur.close()
    
    if not health_data:
        flash('No health data found. Please create new entry.')
        return redirect(url_for('user.health_form'))
    
    # The height in the database is already in decimal feet format (e.g. 5.5)
    # We just need to pass it directly to the form without conversion
    if health_data:
        height_decimal = float(health_data[2])
        print(f"DEBUG: Height from DB in edit form: {height_decimal}")
        
        # Create a modified health_data tuple with the height
        health_data_list = list(health_data)
        health_data_list[2] = height_decimal  # Use the direct height value
        health_data = tuple(health_data_list)
    
    return render_template('healthForm.html', health_data=health_data)

@user_bp.route('/edit_health_data', methods=['POST'])
def edit_health_data():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
    
    try:
        # Get form data - height already in decimal feet (e.g., 5.6 for 5'6")
        height = float(request.form.get('height', 0))
        weight = float(request.form.get('weight', 0))
        age = int(request.form.get('age', 0))
        
        # Health conditions
        diabetes = request.form.get('diabetes', 'none')
        bp = request.form.get('bloodPressure', 'normal')
        cholesterol = request.form.get('cholesterol', 'normal')
        
        # Calculate BMI using the height in feet
        if height > 0:
            # Convert height to inches for BMI calculation
            height_inches = (int(height) * 12) + ((height % 1) * 12)
            # Convert weight from kg to lbs for imperial BMI calculation
            weight_lbs = weight * 2.20462
            # Calculate BMI using imperial formula: (weight in pounds * 703) / (height in inches)²
            bmi = (weight_lbs * 703) / (height_inches * height_inches)
            # Round BMI to 1 decimal place
            bmi = round(bmi, 1)
        else:
            bmi = 0
            
        # Validate inputs
        if weight <= 0:
            flash('Invalid weight value. Please enter a valid weight.', 'danger')
            return redirect(url_for('user.health_form'))
            
        if height <= 0:
            flash('Invalid height value. Please enter a valid height.', 'danger')
            return redirect(url_for('user.health_form'))
        
        # Update database
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        cur.execute("""
            UPDATE health_data 
            SET height = %s, weight = %s, bmi = %s, age = %s,
                diabetes = %s, bp = %s, cholesterol = %s
            WHERE user_id = %s
        """, (
            height, weight, bmi, age,
            diabetes, bp, cholesterol,
            session['user_id']
        ))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Health data updated successfully!', 'success')
        return redirect(url_for('user.profile'))
        
    except Exception as e:
        flash(f'Error updating health data: {str(e)}', 'danger')
        return redirect(url_for('user.edit_health_data_form'))

@user_bp.route('/submit_health_data', methods=['POST'])
def submit_health_data():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))

    try:
        # Get form data - height already in decimal feet (e.g., 5.6 for 5'6")
        height = float(request.form.get('height', 0))
        weight = float(request.form.get('weight', 0))
        age = int(request.form.get('age', 0))
        
        print(f"DEBUG: Submitting health data - height from form: {height}")
        
        # Health conditions
        diabetes = request.form.get('diabetes', 'none')
        bp_value = request.form.get('bloodPressure', 'normal')
        cholesterol_value = request.form.get('cholesterol', 'normal')
        
        # Calculate BMI using the height in feet
        if height > 0:
            # Convert height to inches for BMI calculation
            height_inches = (int(height) * 12) + ((height % 1) * 12)
            # Convert weight from kg to lbs for imperial BMI calculation
            weight_lbs = weight * 2.20462
            # Calculate BMI using imperial formula: (weight in pounds * 703) / (height in inches)²
            bmi = (weight_lbs * 703) / (height_inches * height_inches)
            # Round BMI to 1 decimal place
            bmi = round(bmi, 1)
        else:
            bmi = 0
            
        # Validate inputs
        if weight <= 0:
            flash('Invalid weight value. Please enter a valid weight.', 'danger')
            return redirect(url_for('user.health_form'))
            
        if height <= 0:
            flash('Invalid height value. Please enter a valid height.', 'danger')
            return redirect(url_for('user.health_form'))
        
        # Determine blood pressure and cholesterol categories
        bp = 'high' if bp_value == 'high' else 'normal'
        cholesterol = 'high' if cholesterol_value == 'high' else 'normal'
        
        # Save to database
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        # Check if user already has health data
        cur.execute("SELECT * FROM health_data WHERE user_id = %s", (session['user_id'],))
        user_health_data = cur.fetchone()
        
        if user_health_data:
            # Update existing record
            cur.execute("""
                UPDATE health_data 
                SET height = %s, weight = %s, bmi = %s, age = %s,
                    diabetes = %s, bp = %s, cholesterol = %s
                WHERE user_id = %s
            """, (
                height, weight, bmi, age,
                diabetes, bp, cholesterol,
                session['user_id']
            ))
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO health_data 
                (user_id, height, weight, bmi, age, diabetes, bp, cholesterol)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'], height, weight, bmi, age,
                diabetes, bp, cholesterol
            ))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Health data saved successfully!', 'success')
        return redirect(url_for('user.profile'))
        
    except Exception as e:
        flash(f'Error saving health data: {str(e)}', 'danger')
        return redirect(url_for('user.health_form'))

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Access denied, please log in.', 'warning')
        return redirect(url_for('product.landing_page'))
    
    user_id = session['user_id']
    mysql = g.mysql
    
    # Handle profile update submissions
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET username = %s, email = %s WHERE id = %s", (name, email, user_id))
            
            # Handle profile image upload
            if 'profile_image' in request.files:
                image = request.files['profile_image']
                if image and allowed_file(image.filename):
                    image_data = image.read()
                    cur.execute("UPDATE users SET profile_image = %s WHERE id = %s", (image_data, user_id))
            
            mysql.connection.commit()
            cur.close()
            flash('Profile updated successfully.', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
            if 'Authentication plugin' in str(e):
                flash('Database connection error. Please contact administrator.', 'danger')
        
        return redirect(url_for('user.profile'))
    
    # Get user data and health information for display
    try:
        cur = mysql.connection.cursor()
        
        # Get user data
        cur.execute("SELECT username, email, profile_image FROM users WHERE id = %s", [user_id])
        user_data = cur.fetchone()
        
        if not user_data:
            flash('User data not found.', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Get health data
        cur.execute("""
            SELECT * FROM health_data 
            WHERE user_id = %s 
            ORDER BY id DESC LIMIT 1
        """, (user_id,))
        health_info = cur.fetchone()
        
        cur.close()
        
        username, email, profile_image = user_data
        image_url = url_for('auth.get_profile_image') if profile_image else url_for('static', filename='default-avatar.png')
        
        # Format health_info to display height correctly
        formatted_health_info = None
        if health_info:
            # Get the exact height value from the database without modifications
            height_decimal = float(health_info[2])  # Make sure to convert to float
            print(f"DEBUG: Raw height from DB: {health_info[2]}, converted to float: {height_decimal}")
            
            # Don't convert for display - just show the height value as stored
            feet = height_decimal
            inches = 0
            
            # Create a dictionary to make accessing health data easier in the template
            formatted_health_info = {
                'id': health_info[0],
                'user_id': health_info[1],
                'height': height_decimal,  # Store the exact height value from DB
                'feet': feet,
                'inches': inches,
                'weight': health_info[3],
                'bmi': health_info[4],
                'age': health_info[5],
                'diabetes': health_info[6],
                'bp': health_info[7],
                'cholesterol': health_info[8]
            }
        
        return render_template('profile.html', 
                              username=username, 
                              email=email, 
                              image_url=image_url, 
                              health_info=formatted_health_info)
    
    except Exception as e:
        flash(f'Error fetching user profile: {str(e)}', 'danger')
        if 'Authentication plugin' in str(e):
            # Fix for authentication plugin error
            flash('Please try again in a moment while we fix the database connection.', 'info')
            
            # Try to reconnect with correct plugin
            try:
                app = g.app
                app.config['MYSQL_AUTH_PLUGIN'] = 'mysql_native_password'
                mysql.reconnect()
                flash('Connection restored. Please refresh the page.', 'success')
            except:
                pass
            
        return redirect(url_for('product.landing_page')) 