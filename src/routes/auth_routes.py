from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from flask_bcrypt import Bcrypt
import os
import io
import base64
from werkzeug.utils import secure_filename
from flask import send_file
from utils.common import allowed_file

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if confirm_password exists in the form data
        if 'confirm_password' in request.form:
            confirm_password = request.form['confirm_password']
            
            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('auth.signup'))
        
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        # Check if email already exists
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user:
            flash('Email already registered', 'danger')
            cur.close()
            return redirect(url_for('auth.signup'))
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Insert new user
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                    (username, email, hashed_password))
        mysql.connection.commit()
        
        # Get the newly created user_id
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_id = cur.fetchone()[0]
        cur.close()
        
        # Set session
        session['user_id'] = user_id
        session['user_email'] = email
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('user.health_form'))
        
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        # First check if user exists at all
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            # User doesn't exist in users table
            flash('Please sign up first', 'danger')
            cur.close()
            return redirect(url_for('auth.login'))
        
        # Now verify password for existing user
        if not bcrypt.check_password_hash(user[3], password):
            flash('Invalid password', 'danger')
            cur.close()
            return redirect(url_for('auth.login'))
        
        # User exists and password is correct - check health data
        session['user_id'] = user[0]
        session['user_email'] = user[2]
        
        # Check for existing health data
        cur.execute("SELECT * FROM health_data WHERE user_id = %s", (user[0],))
        health_data = cur.fetchone()
        cur.close()
        
        flash('Login successful!', 'success')
        
        if health_data:
            return redirect(url_for('product.landing_page'))
        else:
            return redirect(url_for('user.health_form'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('product.landing_page'))

@auth_bp.route('/get_profile_image')
def get_profile_image():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    mysql = g.mysql
    cur = mysql.connection.cursor()
    cur.execute("SELECT profile_image FROM users WHERE id = %s", [user_id])
    profile_image = cur.fetchone()[0]
    cur.close()
    if profile_image:
        return send_file(io.BytesIO(profile_image), mimetype='image/png')
    else:
        return redirect(url_for('static', filename='default-avatar.png'))

@auth_bp.route('/save-profile-image', methods=['POST'])
def save_profile_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in first'})
    
    try:
        # Get the image data from the request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'message': 'No image data provided'})
        
        # Get the base64 image data
        image_data = data['image']
        
        # Check if the image data is empty
        if not image_data:
            return jsonify({'success': False, 'message': 'Empty image data received'})
        
        # Check if the image is too large (max 5MB)
        if len(image_data) > 5 * 1024 * 1024:  # 5MB in bytes
            return jsonify({'success': False, 'message': f'Image size too large. Maximum size is 5MB, received {len(image_data) / 1024 / 1024:.2f}MB'})
        
        try:
            # Split if data URL format is used
            if ',' in image_data:
                header, image_data = image_data.split(',', 1)
                print(f"Image format: {header}")  # Log the image format
            
            # Decode base64 data
            try:
                binary_data = base64.b64decode(image_data)
                print(f"Decoded image size: {len(binary_data)} bytes")  # Log the decoded size
            except base64.binascii.Error as e:
                return jsonify({'success': False, 'message': f'Invalid base64 encoding: {str(e)}'})
            
            # Verify the decoded data is not empty
            if not binary_data:
                return jsonify({'success': False, 'message': 'Decoded image data is empty'})
            
            # Save to database
            try:
                mysql = g.mysql
                cur = mysql.connection.cursor()
                cur.execute("UPDATE users SET profile_image = %s WHERE id = %s", 
                           (binary_data, session['user_id']))
                mysql.connection.commit()
                cur.close()
                
                return jsonify({'success': True, 'message': 'Image saved successfully'})
            except Exception as db_error:
                print(f"Database error: {str(db_error)}")  # Log database errors
                return jsonify({'success': False, 'message': f'Database error: {str(db_error)}'})
            
        except base64.binascii.Error as e:
            return jsonify({'success': False, 'message': f'Invalid image data format: {str(e)}'})
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Log unexpected errors
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'}) 