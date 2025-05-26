# new_backend/profile_queries.py
# Note: This code is adapted from the provided snippet to match the existing schema.sql

def get_user_profile_by_id(db_conn, user_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # First, get the user's basic info and role (user_type in DB)
        # Using 'state' instead of 'region', 'profile_picture' instead of 'profile_picture_url'
        # Aliasing user_type as role for consistency in the returned dict
        cursor.execute("""
            SELECT id, username, email, user_type as role, first_name, last_name, 
                   phone_number, address, city, state, zip_code, country, profile_picture, 
                   bio as user_bio, created_at, updated_at 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return None

        # Based on role, fetch role-specific profile
        if user_data['role'] == 'caregiver':
            # Adapted fields for caregiver_profiles
            cursor.execute("""
                SELECT hourly_rate, years_of_experience, skills_description, certifications, 
                       work_schedule_preferences, availability_status, id_verified, 
                       background_check_status, languages_spoken
                FROM caregiver_profiles 
                WHERE user_id = %s
            """, (user_id,))
            caregiver_data = cursor.fetchone()
            if caregiver_data:
                user_data.update(caregiver_data)
        elif user_data['role'] == 'family':
            # Adapted fields for family_profiles
            cursor.execute("""
                SELECT number_of_children, children_ages, specific_needs, location_preferences, 
                       preferred_care_type
                FROM family_profiles 
                WHERE user_id = %s
            """, (user_id,))
            family_data = cursor.fetchone()
            if family_data:
                user_data.update(family_data)
        
        return user_data
    finally:
        cursor.close()

def update_user_profile(db_conn, user_id, role, profile_data: dict):
    cursor = db_conn.cursor()
    try:
        # Common fields for 'users' table, adapted to schema.sql
        # 'state' instead of 'region', 'profile_picture' instead of 'profile_picture_url'
        # 'bio' is also a common field in users table as per schema.sql
        common_fields = ['phone_number', 'address', 'city', 'state', 'zip_code', 'country', 
                         'profile_picture', 'first_name', 'last_name', 'bio'] 
        common_updates = {k: v for k, v in profile_data.items() if k in common_fields and v is not None}
        
        if common_updates:
            set_clauses = ", ".join([f"{key} = %s" for key in common_updates.keys()])
            values = list(common_updates.values())
            values.append(user_id)
            cursor.execute(f"UPDATE users SET {set_clauses}, updated_at = NOW() WHERE id = %s", tuple(values))

        if role == 'caregiver':
            # Adapted fields for 'caregiver_profiles'
            cg_fields = ['hourly_rate', 'years_of_experience', 'skills_description', 
                         'certifications', 'work_schedule_preferences', 'availability_status',
                         'id_verified', 'background_check_status', 'languages_spoken']
            cg_updates = {k: v for k, v in profile_data.items() if k in cg_fields and v is not None}
            
            if cg_updates:
                cursor.execute("SELECT 1 FROM caregiver_profiles WHERE user_id = %s", (user_id,))
                if not cursor.fetchone():
                    # Insert if not exists: ensure all required fields for caregiver_profiles are handled
                    # For simplicity, assuming all fields in cg_updates are sufficient for an insert.
                    # A more robust version would check for NOT NULL constraints from schema.sql.
                    # user_id is required. Other fields might have defaults or be nullable.
                    insert_fields = [k for k in cg_updates.keys()]
                    insert_placeholders = ", ".join(["%s"] * len(insert_fields))
                    insert_values = [cg_updates[k] for k in insert_fields]
                    if insert_fields: # Only proceed if there are fields to insert
                        query = f"INSERT INTO caregiver_profiles (user_id, {', '.join(insert_fields)}) VALUES (%s, {insert_placeholders})"
                        cursor.execute(query, tuple([user_id] + insert_values))
                    else: # If cg_updates was empty or only contained user_id (which is not in cg_fields)
                        # This case might mean only creating an empty profile link if that's desired.
                        # For now, if no specific caregiver fields, we could insert just user_id or skip.
                        # Let's assume if cg_updates is populated, we attempt an insert.
                        # If only user_id is to be inserted (e.g. to create the link)
                        cursor.execute("INSERT INTO caregiver_profiles (user_id) VALUES (%s)", (user_id,))

                else:
                    if cg_updates: # Only proceed if there are fields to update
                        set_clauses = ", ".join([f"{key} = %s" for key in cg_updates.keys()])
                        values = list(cg_updates.values())
                        values.append(user_id)
                        query = f"UPDATE caregiver_profiles SET {set_clauses}, updated_at = NOW() WHERE user_id = %s"
                        cursor.execute(query, tuple(values))

        elif role == 'family':
            # Adapted fields for 'family_profiles'
            fam_fields = ['number_of_children', 'children_ages', 'specific_needs', 
                          'location_preferences', 'preferred_care_type']
            fam_updates = {k: v for k, v in profile_data.items() if k in fam_fields and v is not None}

            if fam_updates:
                cursor.execute("SELECT 1 FROM family_profiles WHERE user_id = %s", (user_id,))
                if not cursor.fetchone():
                    insert_fields = [k for k in fam_updates.keys()]
                    insert_placeholders = ", ".join(["%s"] * len(insert_fields))
                    insert_values = [fam_updates[k] for k in insert_fields]
                    if insert_fields:
                        query = f"INSERT INTO family_profiles (user_id, {', '.join(insert_fields)}) VALUES (%s, {insert_placeholders})"
                        cursor.execute(query, tuple([user_id] + insert_values))
                    else:
                         cursor.execute("INSERT INTO family_profiles (user_id) VALUES (%s)", (user_id,))
                else:
                    if fam_updates:
                        set_clauses = ", ".join([f"{key} = %s" for key in fam_updates.keys()])
                        values = list(fam_updates.values())
                        values.append(user_id)
                        query = f"UPDATE family_profiles SET {set_clauses}, updated_at = NOW() WHERE user_id = %s"
                        cursor.execute(query, tuple(values))
            
        db_conn.commit()
        return True
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_caregiver_public_profile(db_conn, caregiver_user_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Adapted to schema.sql: u.user_type, u.state, u.profile_picture, u.bio
        # cp.years_of_experience, cp.skills_description, cp.work_schedule_preferences etc.
        query = """
        SELECT u.id, u.username, u.email, u.user_type as role, u.first_name, u.last_name, 
               u.city, u.state, u.country, u.profile_picture, u.bio as user_bio, 
               u.created_at AS user_created_at,
               cp.hourly_rate, cp.years_of_experience, cp.skills_description, 
               cp.certifications, cp.work_schedule_preferences, cp.availability_status,
               cp.id_verified, cp.background_check_status, cp.languages_spoken
        FROM users u
        JOIN caregiver_profiles cp ON u.id = cp.user_id
        WHERE u.id = %s AND u.user_type = 'caregiver' AND u.is_active = TRUE
        """
        cursor.execute(query, (caregiver_user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def get_family_public_profile(db_conn, family_user_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Adapted to schema.sql: u.user_type, u.state, u.profile_picture, u.bio
        # fp.number_of_children, fp.children_ages, fp.specific_needs etc.
        query = """
        SELECT u.id, u.username, u.email, u.user_type as role, u.first_name, u.last_name,
               u.city, u.state, u.country, u.profile_picture, u.bio as user_bio,
               u.created_at AS user_created_at,
               fp.number_of_children, fp.children_ages, fp.specific_needs,
               fp.location_preferences, fp.preferred_care_type
        FROM users u
        JOIN family_profiles fp ON u.id = fp.user_id
        WHERE u.id = %s AND u.user_type = 'family' AND u.is_active = TRUE
        """
        cursor.execute(query, (family_user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
