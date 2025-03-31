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
    
    # Get additional fields if available
    activity_level = health_data[7] if len(health_data) > 7 else 'sedentary'
    diet_type = health_data[8] if len(health_data) > 8 else 'none'
    allergies = health_data[9].split(',') if len(health_data) > 9 and health_data[9] else []
    primary_goal = health_data[10] if len(health_data) > 10 else 'maintain_weight'
    
    # Create user profile from database data
    user_profile = {
        'age': age,
        'height': height,  # Height in decimal feet
        'weight': weight,
        'bmi': bmi,
        'diseases': [],
        'activity_level': activity_level,
        'diet_type': diet_type,
        'allergies': allergies,
        'primary_goal': primary_goal
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
            SELECT height, weight, bmi, age, diabetes, bp, cholesterol, 
                   activity_level, diet_type, allergies, primary_goal
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

@diet_bp.route('/get_diet_plan', methods=['POST'])
def get_diet_plan():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        disease = request.form.get('disease', 'none')
        height = float(request.form.get('height'))  # Height in feet
        weight = float(request.form.get('weight'))
        age = int(request.form.get('age'))
        activity_level = request.form.get('activity_level', 'sedentary')
        diet_type = request.form.get('diet_type', 'none')
        allergies = request.form.getlist('allergies[]')
        health_goal = request.form.get('health_goal', 'maintain_weight')
        
        # Get the stored BMI value from the database
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
            
        # Return meal recommendations
        breakfast_list = [breakfast] if breakfast else []
        lunch_list = [lunch] if lunch else []
        dinner_list = [dinner] if dinner else []
        
        return jsonify({
            'breakfast': breakfast_list,
            'lunch': lunch_list,
            'dinner': dinner_list,
            'bmi': bmi,
            'daily_calories': daily_calories,
            'diet_type': diet_type,
            'health_goal': health_goal
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@diet_bp.route("/recommend_meal", methods=["POST"])
def get_meal():
    try:
        data = request.get_json()
        age = int(data["age"])
        weight = float(data["weight"])
        height = float(data["height"])
        disease = data.get("disease", "none").strip()
        activity_level = data.get("activity_level", "sedentary")
        diet_type = data.get("diet_type", "none")
        allergies = data.get("allergies", [])
        health_goal = data.get("health_goal", "maintain_weight")

        print(f"🔍 User Input -> Age: {age}, Weight: {weight}, Height: {height}, Disease: '{disease}', Activity: '{activity_level}', Diet: '{diet_type}', Goal: '{health_goal}'")

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
        
        # Update user's health data in database if user is logged in
        if 'user_id' in session:
            mysql = g.mysql
            cur = mysql.connection.cursor()
            
            # Update or insert health data
            cur.execute("""
                INSERT INTO health_data (user_id, height, weight, age, bmi, activity_level, diet_type, allergies, primary_goal) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                height = VALUES(height),
                weight = VALUES(weight),
                age = VALUES(age),
                bmi = VALUES(bmi),
                activity_level = VALUES(activity_level),
                diet_type = VALUES(diet_type),
                allergies = VALUES(allergies),
                primary_goal = VALUES(primary_goal)
            """, (
                session['user_id'], 
                height, 
                weight, 
                age, 
                bmi,
                activity_level,
                diet_type,
                ','.join(allergies) if isinstance(allergies, list) else allergies,
                health_goal
            ))
            
            mysql.connection.commit()
            cur.close()
        
        # Return meal recommendations and user data
        breakfast_list = [breakfast] if breakfast else []
        lunch_list = [lunch] if lunch else []
        dinner_list = [dinner] if dinner else []
        
        return jsonify({
            "bmi": bmi,
            "daily_calories": daily_calories,
            "breakfast": breakfast_list,
            "lunch": lunch_list,
            "dinner": dinner_list,
            "diet_type": diet_type,
            "health_goal": health_goal
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
        diseases = request.form.getlist('diseases[]')
        diabetes = request.form.get('diabetes', 'none')
        bp = request.form.get('bp', 'normal')
        cholesterol = request.form.get('cholesterol', 'normal')
        other_conditions = request.form.get('other_conditions', '')
        activity_level = request.form.get('activity_level', 'sedentary')
        diet_type = request.form.get('diet_type', 'none')
        allergies = request.form.getlist('allergies[]')
        primary_goal = request.form.get('primary_goal', 'maintain_weight')
        target_weight = float(request.form.get('target_weight', weight))
        
        # Join multiple diseases and allergies with comma
        disease_list = ','.join(diseases) if diseases else 'none'
        allergies_list = ','.join(allergies) if allergies else ''
        
        # Get BMI from database instead of recalculating
        mysql = g.mysql
        cur = mysql.connection.cursor()
        cur.execute("SELECT bmi FROM health_data WHERE user_id = %s", (session['user_id'],))
        bmi_result = cur.fetchone()
        bmi = float(bmi_result[0]) if bmi_result else None
        
        # Update user's health data in database - only update the conditions, not height/weight/age
        # Check if user already has health data
        cur.execute("SELECT * FROM health_data WHERE user_id = %s", (session['user_id'],))
        has_data = cur.fetchone() is not None
        
        if has_data:
            # Update existing health data including the new fields
            try:
                cur.execute("""
                    UPDATE health_data 
                    SET diseases = %s, other_conditions = %s, activity_level = %s,
                        diabetes = %s, bp = %s, cholesterol = %s,
                        diet_type = %s, allergies = %s, primary_goal = %s, target_weight = %s
                    WHERE user_id = %s
                """, (disease_list, other_conditions, activity_level, 
                      diabetes, bp, cholesterol, diet_type, allergies_list, 
                      primary_goal, target_weight, session['user_id']))
            except Exception as e:
                print(f"SQL Error: {str(e)}")
                # Fallback to only updating fields that exist
                cur.execute("""
                    UPDATE health_data 
                    SET diabetes = %s, bp = %s, cholesterol = %s
                    WHERE user_id = %s
                """, (diabetes, bp, cholesterol, session['user_id']))
        else:
            # This shouldn't happen since we redirect users without health data
            # but just in case, create a new record with all data
            try:
                cur.execute("""
                    INSERT INTO health_data 
                    (user_id, height, weight, age, bmi, diseases, other_conditions, 
                     activity_level, diabetes, bp, cholesterol,
                     diet_type, allergies, primary_goal, target_weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], height_decimal, weight, age, bmi, disease_list, 
                      other_conditions, activity_level, diabetes, bp, cholesterol,
                      diet_type, allergies_list, primary_goal, target_weight))
            except Exception as e:
                print(f"SQL Error: {str(e)}")
                # Fallback to insertion with minimal fields
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
        for d in diseases:
            if d and d not in diseases_list:
                diseases_list.append(d)
        
        # Create user profile dictionary for diet plan generation
        user_profile = {
            'height': height_decimal,
            'weight': weight,
            'age': age,
            'bmi': bmi,
            'diseases': diseases_list,
            'other_conditions': other_conditions,
            'activity_level': activity_level,
            'diet_type': diet_type,
            'allergies': allergies,
            'primary_goal': primary_goal,
            'target_weight': target_weight,
            'diabetes': diabetes,
            'bp': bp,
            'cholesterol': cholesterol,
            'name': user_info[0] if user_info else 'User',
            'email': user_info[1] if user_info else ''
        }
        
        # Print debug info about medical conditions
        print(f"DEBUG - User diseases: {diseases_list}")
        print(f"DEBUG - User profile with diseases before diet plan generation: {user_profile['diseases']}")
        
        # Generate diet plan based on user profile
        disease = 'none'
        if user_profile['diseases']:
            if 'diabetes' in user_profile['diseases']:
                disease = 'diabetes'
            elif 'hypertension' in user_profile['diseases']:
                disease = 'hypertension'
            elif 'heart disease' in user_profile['diseases']:
                disease = 'heart disease'
            elif len(user_profile['diseases']) > 0:
                disease = user_profile['diseases'][0]
        
        # Get meal recommendations using height in feet and stored BMI
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age,
            weight=weight,
            height_ft=height_decimal,
            disease=disease,
            stored_bmi=bmi
        )
        
        # Calculate daily calories
        if height_decimal > 0:
            # Use a simpler calorie calculation without feet/inches conversion
            height_m = height_decimal * 0.3048  # Convert height from feet to meters
            # Basic BMR calculation (Harris-Benedict equation)
            bmr = 10 * weight + 6.25 * (height_m * 100) - 5 * age + 5
            daily_calories = int(bmr * 1.2)  # Assuming sedentary activity level
        else:
            daily_calories = 2000  # Default value
        
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
    """
    Diet recommendation page that provides personalized nutrition advice
    based on user profile, BMI, and medical conditions
    """
    try:
        # Get current user from session
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
        diet_plan = create_diet_plan(
            age=user_profile['age'],
            weight=user_profile['weight'],
            height_ft=user_profile['height'],
            disease=disease,
            stored_bmi=user_profile['bmi']
        )
        
        # Store the diet plan in session for later use
        session['diet_plan'] = diet_plan
        
        return render_template('diet_recommendation.html', 
                            user_profile=user_profile, 
                            diet_plan=diet_plan)
                            
    except Exception as e:
        print(f"Database error: {str(e)}")
        flash(f'Error fetching user profile: {str(e)}', 'error')
        return redirect(url_for('user.health_form')) 