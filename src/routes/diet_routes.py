from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from models.diet_plan import recommend_meal, calculate_bmi

diet_bp = Blueprint('diet', __name__)

@diet_bp.route('/diet_plan')
def diet_plan():
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('auth.login'))
    
    # Get user's health data from database
    mysql = g.mysql
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT height, weight, age, bmi, diabetes, bp, cholesterol
        FROM health_data 
        WHERE user_id = %s
    """, (session['user_id'],))
    health_data = cur.fetchone()
    cur.close()
    
    if not health_data:
        flash('Please complete your health profile first')
        return redirect(url_for('user.health_form'))
    
    # Height is already in decimal feet format
    height = float(health_data[0])  # Height in decimal feet (e.g., 5.6)
    weight = float(health_data[1])  # Weight in kg
    age = int(health_data[2])       # Age
    bmi = float(health_data[3])     # BMI
    
    # Convert decimal feet to feet and inches for display
    feet = int(height)
    inches = int((height % 1) * 12)
    
    disease = 'none'
    # Determine disease based on health conditions
    if health_data[4] != 'none':
        disease = 'diabetes'
    elif health_data[5] == 'high':
        disease = 'hypertension'
    
    # Get diet recommendations based on the user's health data
    bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
        age=age, 
        weight=weight, 
        height_ft=height,  # Height in decimal feet
        disease=disease
    )
    
    # Calculate daily calories using imperial units
    if height > 0:
        # Convert height to inches for calorie calculation
        height_inches = (feet * 12) + inches
        # Convert weight to lbs
        weight_lbs = weight * 2.20462
        # Basic BMR calculation (Harris-Benedict equation) - adjusted for imperial
        bmr = 10 * weight + 6.25 * height_inches - 5 * age + 5
        daily_calories = int(bmr * 1.2)  # Assuming sedentary activity level
    else:
        daily_calories = 2000  # Default value
        
    # Format recommendations for the template
    recommendations = {
        'bmi': bmi,
        'bmi_category': bmi_category,
        'daily_calories': daily_calories,
        'breakfast': [breakfast] if breakfast else [],
        'lunch': [lunch] if lunch else [],
        'dinner': [dinner] if dinner else []
    }
    
    # Create user profile with feet and inches
    user_profile = {
        'age': age,
        'height': height,  # Height in decimal feet
        'feet': feet,      # Whole feet part
        'inches': inches,  # Inches part
        'weight': weight,
        'bmi': bmi
    }
    
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
        
        # Get meal recommendations with the correct parameter names
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age, 
            weight=weight, 
            height_ft=height,  # Use height_ft parameter
            disease=disease
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

        # Get meal recommendations with the correct parameter names
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age, 
            weight=weight, 
            height_ft=height,  # Use height_ft parameter instead of height
            disease=disease
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
        
        # Parse height from decimal feet to feet and inches
        feet = int(height_decimal)
        inches = (height_decimal - feet) * 12
        
        # Calculate height in meters for BMI calculation
        height_total_inches = (feet * 12) + inches
        height_meters = height_total_inches * 0.0254
        
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
        
        # Calculate BMI - we'll use the same calculation as in the health profile
        bmi = weight / (height_meters ** 2)
        
        # Update user's health data in database - only update the conditions, not height/weight/age
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
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
                     activity_level, diabetes, bp, cholesterol, height_meters,
                     diet_type, allergies, primary_goal, target_weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], height_meters, weight, age, bmi, disease_list, 
                      other_conditions, activity_level, diabetes, bp, cholesterol, height_meters,
                      diet_type, allergies_list, primary_goal, target_weight))
            except Exception as e:
                print(f"SQL Error: {str(e)}")
                # Fallback to insertion with minimal fields
                cur.execute("""
                    INSERT INTO health_data 
                    (user_id, height, weight, age, bmi, diabetes, bp, cholesterol, height_meters)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], height_meters, weight, age, bmi, 
                      diabetes, bp, cholesterol, height_meters))
        
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
            'height_meters': height_meters,
            'height': height_decimal,
            'feet': feet,
            'inches': inches,
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
        
        # Get meal recommendations
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age,
            weight=weight,
            height_ft=height_decimal,
            disease=disease
        )
        
        # Calculate daily calories
        if height_decimal > 0:
            # Basic BMR calculation (Harris-Benedict equation)
            bmr = 10 * weight + 6.25 * (height_meters * 100) - 5 * age + 5
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
            
        user_id = session['user_id']
        
        # Connect to database and fetch user profile
        mysql = g.mysql
        cur = mysql.connection.cursor()
        
        # Fetch basic user data
        cur.execute('''
            SELECT height, weight, bmi, age, diabetes, bp, cholesterol
            FROM health_data 
            WHERE user_id = %s
            ORDER BY id DESC LIMIT 1
        ''', (user_id,))
        
        health_data = cur.fetchone()
        cur.close()
        
        if not health_data:
            flash('Please complete your health profile first')
            return redirect(url_for('user.health_form'))
        
        # Extract data from the database result
        height = float(health_data[0])     # Height in decimal feet (e.g., 5.6)
        weight = float(health_data[1])     # Weight in kg
        bmi = float(health_data[2])        # BMI from database
        age = int(health_data[3])          # Age
        diabetes = health_data[4]          # Diabetes type
        bp = health_data[5]                # Blood pressure
        cholesterol = health_data[6]       # Cholesterol level
        
        # Convert decimal feet to feet and inches for display
        feet = int(height)
        inches = int((height % 1) * 12)
        
        # Create user profile from database data
        user_profile = {
            'age': age,
            'height': height,  # Height in decimal feet
            'feet': feet,      # Whole feet part
            'inches': inches,  # Inches part
            'weight': weight,
            'bmi': bmi,
            'diseases': [],
            'activity_level': 'sedentary',  # Default value
            'primary_goal': 'maintain_weight'  # Default value
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
        
        # Get meal recommendations using height in feet
        bmi, bmi_category, breakfast, lunch, dinner = recommend_meal(
            age=age,
            weight=weight,
            height_ft=height,  # Height in decimal feet
            disease=disease
        )
        
        # Calculate daily calories using imperial units
        if height > 0:
            # Convert height to inches for calorie calculation
            height_inches = (feet * 12) + inches
            # Convert weight to lbs
            weight_lbs = weight * 2.20462
            # Basic BMR calculation (Harris-Benedict equation) - adjusted for imperial
            bmr = 10 * weight + 6.25 * height_inches - 5 * age + 5
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
        
        return render_template('diet_recommendation.html', 
                            user_profile=user_profile, 
                            diet_plan=diet_plan)
                            
    except Exception as e:
        print(f"Database error: {str(e)}")
        flash(f'Error fetching user profile: {str(e)}', 'error')
        return redirect(url_for('user.health_form'))

@diet_bp.route('/meal_alternatives/<meal_type>')
def meal_alternatives(meal_type):
    """
    Display alternative meal options for a specific meal type
    """
    try:
        # Validate meal type
        if meal_type not in ['breakfast', 'lunch', 'dinner']:
            flash('Invalid meal type requested', 'error')
            return redirect(url_for('diet.diet_recommendation'))
        
        # Get diet plan from session if available
        diet_plan = session.get('diet_plan')
        
        # In a real app, these would be generated by a recommendation algorithm
        # based on user preferences and dietary restrictions
        breakfast_alternatives = [
            {
                'name': 'Protein-Packed Breakfast',
                'meal_items': [
                    {'name': 'Greek yogurt with berries', 'quantity': '1 cup'},
                    {'name': 'Scrambled eggs', 'quantity': '2 large'},
                    {'name': 'Whole grain toast', 'quantity': '1 slice'}
                ],
                'calories': 400
            },
            {
                'name': 'Overnight Oats',
                'meal_items': [
                    {'name': 'Rolled oats', 'quantity': '1/2 cup'},
                    {'name': 'Almond milk', 'quantity': '1/2 cup'},
                    {'name': 'Chia seeds', 'quantity': '1 tbsp'},
                    {'name': 'Sliced banana', 'quantity': '1/2'}
                ],
                'calories': 350
            },
            {
                'name': 'Avocado Toast',
                'meal_items': [
                    {'name': 'Whole grain bread', 'quantity': '2 slices'},
                    {'name': 'Avocado', 'quantity': '1/2'},
                    {'name': 'Cherry tomatoes', 'quantity': '5'},
                    {'name': 'Poached egg', 'quantity': '1'}
                ],
                'calories': 420
            },
            {
                'name': 'Fruit Smoothie Bowl',
                'meal_items': [
                    {'name': 'Frozen mixed berries', 'quantity': '1 cup'},
                    {'name': 'Banana', 'quantity': '1'},
                    {'name': 'Plant-based protein powder', 'quantity': '1 scoop'},
                    {'name': 'Granola topping', 'quantity': '2 tbsp'}
                ],
                'calories': 380
            }
        ]
        
        lunch_alternatives = [
            {
                'name': 'Mediterranean Bowl',
                'meal_items': [
                    {'name': 'Quinoa', 'quantity': '1/2 cup'},
                    {'name': 'Grilled chicken', 'quantity': '4 oz'},
                    {'name': 'Cucumber', 'quantity': '1/2'},
                    {'name': 'Cherry tomatoes', 'quantity': '5'},
                    {'name': 'Feta cheese', 'quantity': '1 oz'},
                    {'name': 'Olive oil dressing', 'quantity': '1 tbsp'}
                ],
                'calories': 450
            },
            {
                'name': 'Hearty Lentil Soup',
                'meal_items': [
                    {'name': 'Lentil soup', 'quantity': '1.5 cups'},
                    {'name': 'Whole grain roll', 'quantity': '1'},
                    {'name': 'Mixed green salad', 'quantity': '1 cup'},
                    {'name': 'Olive oil and vinegar', 'quantity': '1 tbsp'}
                ],
                'calories': 400
            },
            {
                'name': 'Tuna Salad Wrap',
                'meal_items': [
                    {'name': 'Whole grain wrap', 'quantity': '1'},
                    {'name': 'Tuna (packed in water)', 'quantity': '3 oz'},
                    {'name': 'Greek yogurt', 'quantity': '2 tbsp'},
                    {'name': 'Diced celery and onion', 'quantity': '1/4 cup'},
                    {'name': 'Lettuce', 'quantity': '1/2 cup'}
                ],
                'calories': 350
            },
            {
                'name': 'Veggie Buddha Bowl',
                'meal_items': [
                    {'name': 'Brown rice', 'quantity': '1/2 cup'},
                    {'name': 'Roasted sweet potato', 'quantity': '1/2 cup'},
                    {'name': 'Chickpeas', 'quantity': '1/2 cup'},
                    {'name': 'Steamed broccoli', 'quantity': '1 cup'},
                    {'name': 'Tahini dressing', 'quantity': '1 tbsp'}
                ],
                'calories': 420
            }
        ]
        
        dinner_alternatives = [
            {
                'name': 'Grilled Salmon Plate',
                'meal_items': [
                    {'name': 'Grilled salmon', 'quantity': '4 oz'},
                    {'name': 'Quinoa', 'quantity': '1/2 cup'},
                    {'name': 'Roasted asparagus', 'quantity': '1 cup'},
                    {'name': 'Lemon-dill sauce', 'quantity': '1 tbsp'}
                ],
                'calories': 450
            },
            {
                'name': 'Low-Carb Turkey Chili',
                'meal_items': [
                    {'name': 'Lean ground turkey chili', 'quantity': '1.5 cups'},
                    {'name': 'Brown rice', 'quantity': '1/3 cup'},
                    {'name': 'Avocado slices', 'quantity': '1/4 avocado'},
                    {'name': 'Greek yogurt topping', 'quantity': '2 tbsp'}
                ],
                'calories': 480
            },
            {
                'name': 'Heart-Healthy Vegetable Stir Fry',
                'meal_items': [
                    {'name': 'Tofu', 'quantity': '4 oz'},
                    {'name': 'Mixed vegetables', 'quantity': '2 cups'},
                    {'name': 'Brown rice', 'quantity': '1/2 cup'},
                    {'name': 'Low-sodium soy sauce', 'quantity': '1 tsp'}
                ],
                'calories': 400
            },
            {
                'name': 'Gluten-Free Zucchini Pasta',
                'meal_items': [
                    {'name': 'Zucchini noodles', 'quantity': '2 cups'},
                    {'name': 'Turkey meatballs', 'quantity': '3 (1 oz each)'},
                    {'name': 'Marinara sauce', 'quantity': '1/2 cup'},
                    {'name': 'Parmesan cheese', 'quantity': '1 tbsp'}
                ],
                'calories': 350
            }
        ]
        
        meal_options = {
            'breakfast': breakfast_alternatives,
            'lunch': lunch_alternatives,
            'dinner': dinner_alternatives
        }
        
        return render_template(
            'meal_alternatives.html',
            meal_type=meal_type,
            alternatives=meal_options[meal_type]
        )
    except Exception as e:
        flash(f'Error loading meal alternatives: {str(e)}', 'error')
        return redirect(url_for('diet.diet_recommendation')) 