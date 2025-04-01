from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from models.diet_plan import recommend_meal, calculate_bmi

diet_bp = Blueprint('diet', __name__)

# Helper Functions
def calculate_daily_calories(weight, height_ft, age):
    """
    Calculate daily calorie needs based on weight, height, and age.
    
    Args:
        weight (float): Weight in kilograms
        height_ft (float): Height in decimal feet
        age (int): Age in years
        
    Returns:
        int: Estimated daily calorie needs
    """
    if height_ft <= 0:
        return 2000  # Default value
        
    # Convert height from feet to meters
    height_m = height_ft * 0.3048
    
    # Basic BMR calculation (Harris-Benedict equation)
    bmr = 10 * weight + 6.25 * (height_m * 100) - 5 * age + 5
    daily_calories = int(bmr * 1.2)  # Assuming sedentary activity level
    
    return daily_calories

def get_primary_disease(diseases, diabetes, bp, cholesterol):
    """
    Determine the primary disease for diet recommendations.
    
    Args:
        diseases (list): List of disease names
        diabetes (str): Diabetes status
        bp (str): Blood pressure status
        cholesterol (str): Cholesterol status
        
    Returns:
        str: Primary disease name for diet recommendations
    """
    disease_list = []
    
    # Add diseases based on health data
    if diabetes != 'none':
        disease_list.append('diabetes')
    
    if bp == 'high':
        disease_list.append('hypertension')
        
    if cholesterol == 'high':
        disease_list.append('heart disease')
    
    # Add other diseases
    for d in diseases:
        if d and d not in disease_list:
            disease_list.append(d)
    
    # Select primary disease for diet recommendations
    if not disease_list:
        return 'none'
        
    if 'diabetes' in disease_list:
        return 'diabetes'
    elif 'hypertension' in disease_list:
        return 'hypertension'
    elif 'heart disease' in disease_list:
        return 'heart disease'
    else:
        return disease_list[0]

def create_user_profile(health_data):
    """
    Create a user profile from health data.
    
    Args:
        health_data (tuple): Database result containing health information
        
    Returns:
        dict: User profile dictionary
    """
    height = float(health_data[0])     # Height in decimal feet (e.g., 5.5)
    weight = float(health_data[1])     # Weight in kg
    bmi = float(health_data[2])        # BMI from database
    age = int(health_data[3])          # Age
    diabetes = health_data[4]          # Diabetes type
    bp = health_data[5]                # Blood pressure
    cholesterol = health_data[6]       # Cholesterol level
    
    # Create user profile from database data
    user_profile = {
        'age': age,
        'height': height,  # Height in decimal feet
        'weight': weight,
        'bmi': bmi,
        'diseases': []
    }
    
    # Add diseases based on health data
    if diabetes != 'none':
        user_profile['diseases'].append('diabetes')
    
    if bp == 'high':
        user_profile['diseases'].append('hypertension')
        
    if cholesterol == 'high':
        user_profile['diseases'].append('heart disease')
        
    if bmi >= 30:
        user_profile['diseases'].append('obesity')
        
    return user_profile

def create_diet_plan(age, weight, height_ft, disease, stored_bmi):
    """
    Create a diet plan based on user information.
    
    Args:
        age (int): Age in years
        weight (float): Weight in kilograms
        height_ft (float): Height in decimal feet
        disease (str): Primary disease
        stored_bmi (float): BMI from database
        
    Returns:
        dict: Diet plan dictionary with meal recommendations
    """
    # Get meal recommendations
    bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
        age=age,
        weight=weight,
        height_ft=height_ft,
        disease=disease,
        stored_bmi=stored_bmi
    )
    
    # Calculate daily calories
    daily_calories = calculate_daily_calories(weight, height_ft, age)
    
    # Determine calorie adjustment suggestion based on BMI category
    calorie_suggestion = ""
    adjusted_calories = daily_calories
    
    if bmi_category.lower() == "obese":
        # Reduce by 20% for obese
        adjusted_calories = int(daily_calories * 0.8)
        calorie_suggestion = "Based on your BMI category (Obese), we suggest reducing your daily calorie intake by 20% to support healthy weight loss."
    elif bmi_category.lower() == "overweight":
        # Reduce by 10% for overweight
        adjusted_calories = int(daily_calories * 0.9)
        calorie_suggestion = "Based on your BMI category (Overweight), we suggest reducing your daily calorie intake by 10% to achieve a healthy weight."
    elif bmi_category.lower() == "underweight":
        # Increase by 10% for underweight
        adjusted_calories = int(daily_calories * 1.1)
        calorie_suggestion = "Based on your BMI category (Underweight), we suggest increasing your daily calorie intake by 10% to support healthy weight gain."
    else:  # Normal weight
        calorie_suggestion = "Your BMI falls within the normal range. The suggested calorie intake aims to maintain your current weight."
    
    # Create diet plan
    return {
        "daily_calories": daily_calories,
        "adjusted_calories": adjusted_calories,
        "calorie_suggestion": calorie_suggestion,
        "bmi": bmi,
        "bmi_category": bmi_category,
        "breakfast": [breakfast] if breakfast else [],
        "lunch": [lunch] if lunch else [],
        "dinner": [dinner] if dinner else [],
        "medical_condition": disease
    }

def get_profile_by_user_id(user_id):
    """
    Get user profile data from the database.
    
    Args:
        user_id (int): The user ID to retrieve profile data for
        
    Returns:
        dict: Dictionary with user profile data
        tuple: Raw database result
    """
    try:
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        # Get health data
        cur.execute("""
            SELECT height, weight, bmi, age, diabetes, bp, cholesterol
            FROM health_data 
            WHERE user_id = %s
            ORDER BY id DESC LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        cur.close()
        
        if not result:
            return {}, None
            
        # Create profile dictionary using helper function
        profile = create_user_profile(result)
        return profile, result
        
    except Exception as e:
        print(f"Error getting user profile: {str(e)}")
        return {}, None

# Routes

@diet_bp.route('/diet_plan')
def diet_plan():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
    
    # Get user profile using helper function
    user_profile, health_data = get_profile_by_user_id(session['user_id'])
    
    if not health_data:
        flash('Please complete your health profile first')
        return redirect(url_for('user.health_form'))
    
    # Determine primary disease for diet recommendations
    disease = get_primary_disease(
        user_profile.get('diseases', []),
        health_data[4],  # diabetes
        health_data[5],  # bp
        health_data[6]   # cholesterol
    )
    
    # Create diet plan using helper function
    recommendations = create_diet_plan(
        age=user_profile['age'],
        weight=user_profile['weight'],
        height_ft=user_profile['height'],
        disease=disease,
        stored_bmi=user_profile['bmi']
    )
    
    return render_template('diet_plan.html', 
                          user_profile=user_profile,
                          recommendations=recommendations)

@diet_bp.route("/recommend_meal", methods=["POST"])
def get_meal():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        # Get basic required fields
        age = int(data.get("age"))
        weight = float(data.get("weight"))
        height = float(data.get("height"))
        disease = data.get("disease", "none").strip()

        print(f"🔍 User Input -> Age: {age}, Weight: {weight}, Height: {height}, Disease: '{disease}'")

        # Get stored BMI from database if user is logged in
        stored_bmi = None
        if 'user_id' in session:
            mysql = g.mysql
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT bmi
                FROM health_data 
                WHERE user_id = %s
            """, (session['user_id'],))
            health_data = cur.fetchone()
            cur.close()
            
            stored_bmi = float(health_data[0]) if health_data else None

        # Get meal recommendations with the stored BMI
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age, 
            weight=weight, 
            height_ft=height,  # Use height_ft parameter
            disease=disease,
            stored_bmi=stored_bmi
        )

        # Calculate daily calories based on weight and height
        if height > 0:
            height_m = height * 0.3048  # Convert height from feet to meters
            # Basic BMR calculation (Harris-Benedict equation)
            bmr = 10 * weight + 6.25 * (height_m * 100) - 5 * age + 5
            daily_calories = int(bmr * 1.2)  # Assuming sedentary activity level
        else:
            daily_calories = 2000  # Default value
        
        # Return meal recommendations and user data
        breakfast_list = [breakfast] if breakfast else []
        lunch_list = [lunch] if lunch else []
        dinner_list = [dinner] if dinner else []
        
        return jsonify({
            "bmi": bmi,
            "daily_calories": daily_calories,
            "breakfast": breakfast_list,
            "lunch": lunch_list,
            "dinner": dinner_list
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)})

@diet_bp.route("/update_diet_recommendation", methods=["POST"])
def update_diet_recommendation():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
        
    try:
        # Get form data - these are readonly so they should match the database
        age = int(request.form.get('age'))
        weight = float(request.form.get('weight'))
        height_decimal = float(request.form.get('height', 0))
        
        # Get health conditions - these can be updated by the user
        diabetes = request.form.get('diabetes', 'none')
        bp = request.form.get('bp', 'normal')
        cholesterol = request.form.get('cholesterol', 'normal')
        
        # Get BMI from database instead of recalculating
        mysql = g.mysql
        cur = mysql.connection.cursor()
        cur.execute("SELECT bmi FROM health_data WHERE user_id = %s", (session['user_id'],))
        bmi_result = cur.fetchone()
        bmi = float(bmi_result[0]) if bmi_result else None
        
        # Check if user already has health data
        cur.execute("SELECT * FROM health_data WHERE user_id = %s", (session['user_id'],))
        has_data = cur.fetchone() is not None
        
        if has_data:
            # Update existing health data
            cur.execute("""
                UPDATE health_data 
                SET diabetes = %s, bp = %s, cholesterol = %s
                WHERE user_id = %s
            """, (diabetes, bp, cholesterol, session['user_id']))
        else:
            # Create a new record with all data
            cur.execute("""
                INSERT INTO health_data 
                (user_id, height, weight, age, bmi, diabetes, bp, cholesterol)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], height_decimal, weight, age, bmi, 
                  diabetes, bp, cholesterol))
        
        mysql.connection.commit()
        
        # Get user's name and email
        cur.execute("SELECT username, email FROM users WHERE id = %s", (session['user_id'],))
        user_info = cur.fetchone()
        cur.close()
        
        # Create a list of diseases for display
        diseases_list = []
        if diabetes != 'none':
            diseases_list.append('diabetes')
        if bp == 'high':
            diseases_list.append('hypertension')
        if cholesterol == 'high':
            diseases_list.append('heart disease')
        
        # Create user profile dictionary for diet plan generation
        user_profile = {
            'height': height_decimal,
            'weight': weight,
            'age': age,
            'bmi': bmi,
            'diseases': diseases_list,
            'diabetes': diabetes,
            'bp': bp,
            'cholesterol': cholesterol,
            'name': user_info[0] if user_info else 'User',
            'email': user_info[1] if user_info else ''
        }
        
        # Print debug info about medical conditions
        print(f"DEBUG - User diseases: {diseases_list}")
        
        # Generate diet plan based on user profile
        disease = 'none'
        if diseases_list:
            if 'diabetes' in diseases_list:
                disease = 'diabetes'
            elif 'hypertension' in diseases_list:
                disease = 'hypertension'
            elif 'heart disease' in diseases_list:
                disease = 'heart disease'
            elif len(diseases_list) > 0:
                disease = diseases_list[0]
        
        # Get meal recommendations using height in feet and stored BMI
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age,
            weight=weight,
            height_ft=height_decimal,
            disease=disease,
            stored_bmi=bmi
        )
        
        # Calculate daily calories
        daily_calories = calculate_daily_calories(weight, height_decimal, age)
        
        # Create diet plan
        diet_plan = {
            "daily_calories": daily_calories,
            "bmi": bmi,
            "bmi_category": bmi_category,
            "breakfast": [breakfast] if breakfast else [],
            "lunch": [lunch] if lunch else [],
            "dinner": [dinner] if dinner else [],
            "medical_condition": disease
        }
        
        # Store the diet plan in session for later use
        session['diet_plan'] = diet_plan
        
        flash('Diet profile updated successfully!')
        return render_template('diet_recommendation.html', 
                              user_profile=user_profile,
                              recommendations=diet_plan,
                              diet_plan=diet_plan)
        
    except Exception as e:
        print(f"Error updating diet profile: {str(e)}")
        flash(f'Error updating diet profile: {str(e)}')
        return redirect(url_for('diet.diet_recommendation'))

@diet_bp.route("/diet_recommendation")
def diet_recommendation():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
        
    try:
        # Get user profile
        user_profile, health_data = get_profile_by_user_id(session['user_id'])
        
        if not health_data:
            flash('Please complete your health profile first')
            return redirect(url_for('user.health_form'))
            
        # Get primary disease for recommendations
        disease = get_primary_disease(
            user_profile.get('diseases', []),
            health_data[4],  # diabetes
            health_data[5],  # bp
            health_data[6]   # cholesterol
        )
        
        # Create diet plan
        diet_plan = create_diet_plan(
            age=user_profile['age'],
            weight=user_profile['weight'],
            height_ft=user_profile['height'],
            disease=disease,
            stored_bmi=user_profile['bmi']
        )
        
        return render_template(
            'diet_recommendation.html',
            diet_plan=diet_plan,
            user_profile=user_profile
        )
        
    except Exception as e:
        flash(f'Error generating diet recommendation: {str(e)}')
        return redirect(url_for('user.profile')) 