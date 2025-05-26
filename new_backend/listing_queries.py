# new_backend/listing_queries.py

def list_caregiver_profiles(db_conn, filters: dict, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    
    # Adapted to schema.sql:
    # u.user_type AS role, u.bio AS user_bio
    # cp.availability_status AS availability_details, cp.certifications AS certifications
    base_query = """
    SELECT u.id, u.username, u.email, u.user_type AS role, u.first_name, u.last_name, 
           u.city, u.state AS region, u.country, u.profile_picture AS profile_picture_url, 
           u.created_at AS user_created_at, u.bio AS user_bio,
           cp.id AS caregiver_profile_id, cp.hourly_rate, 
           cp.availability_status AS availability_details, 
           cp.years_of_experience AS experience_years, 
           cp.skills_description AS specializations, 
           cp.certifications AS certifications,
           cp.languages_spoken, cp.id_verified, cp.background_check_status -- Added more fields from caregiver_profiles
    FROM users u
    JOIN caregiver_profiles cp ON u.id = cp.user_id
    WHERE u.user_type = 'caregiver' AND u.is_active = TRUE
    """
    
    count_query = """
    SELECT COUNT(*) as total_count
    FROM users u
    JOIN caregiver_profiles cp ON u.id = cp.user_id
    WHERE u.user_type = 'caregiver' AND u.is_active = TRUE
    """

    where_clauses = []
    params = []

    if filters.get('city'):
        where_clauses.append("u.city LIKE %s")
        params.append(f"%{filters['city']}%")
    if filters.get('state'): # 'state' filter key, mapped from 'region' in Pydantic
        where_clauses.append("u.state LIKE %s")
        params.append(f"%{filters['state']}%")
    if filters.get('country'):
        where_clauses.append("u.country LIKE %s")
        params.append(f"%{filters['country']}%")
    if filters.get('min_hourly_rate') is not None:
        where_clauses.append("cp.hourly_rate >= %s")
        params.append(filters['min_hourly_rate'])
    if filters.get('max_hourly_rate') is not None:
        where_clauses.append("cp.hourly_rate <= %s")
        params.append(filters['max_hourly_rate'])
    if filters.get('min_experience_years') is not None:
        where_clauses.append("cp.years_of_experience >= %s") # schema.sql: years_of_experience
        params.append(filters['min_experience_years'])
    if filters.get('specializations'): # Mapped to skills_description
         where_clauses.append("cp.skills_description LIKE %s") # schema.sql: skills_description
         params.append(f"%{filters['specializations']}%")
    if filters.get('languages_spoken'):
        where_clauses.append("cp.languages_spoken LIKE %s")
        params.append(f"%{filters['languages_spoken']}%")
    if filters.get('availability_status'): # Direct match to availability_status
        where_clauses.append("cp.availability_status = %s")
        params.append(filters['availability_status'])


    if where_clauses:
        clause_str = " AND " + " AND ".join(where_clauses)
        base_query += clause_str
        count_query += clause_str
            
    cursor.execute(count_query, tuple(params))
    total_count_result = cursor.fetchone()
    total_count = total_count_result['total_count'] if total_count_result else 0

    base_query += " ORDER BY u.created_at DESC"
    offset = (page - 1) * page_size
    base_query += " LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    
    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    cursor.close()
    
    return results, total_count

def list_family_profiles(db_conn, filters: dict, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)

    # Adapted to schema.sql:
    # u.user_type AS role, u.bio AS user_bio
    # fp.preferred_care_type AS care_needs
    # Added: fp.number_of_children, fp.children_ages, fp.specific_needs, fp.location_preferences
    base_query = """
    SELECT u.id, u.username, u.email, u.user_type AS role, u.first_name, u.last_name,
           u.city, u.state AS region, u.country, u.profile_picture AS profile_picture_url, 
           u.created_at AS user_created_at, u.bio AS user_bio,
           fp.id as family_profile_id, 
           fp.number_of_children, fp.children_ages, fp.specific_needs, 
           fp.location_preferences, fp.preferred_care_type AS care_needs
    FROM users u
    JOIN family_profiles fp ON u.id = fp.user_id
    WHERE u.user_type = 'family' AND u.is_active = TRUE
    """
    count_query = """
    SELECT COUNT(*) as total_count
    FROM users u
    JOIN family_profiles fp ON u.id = fp.user_id
    WHERE u.user_type = 'family' AND u.is_active = TRUE
    """
    
    where_clauses = []
    params = []

    if filters.get('city'):
        where_clauses.append("u.city LIKE %s")
        params.append(f"%{filters['city']}%")
    if filters.get('state'): # 'state' filter key, mapped from 'region' in Pydantic
        where_clauses.append("u.state LIKE %s")
        params.append(f"%{filters['state']}%")
    if filters.get('country'):
        where_clauses.append("u.country LIKE %s")
        params.append(f"%{filters['country']}%")
    if filters.get('care_needs'): # Mapped to preferred_care_type
        where_clauses.append("fp.preferred_care_type LIKE %s") # schema.sql: preferred_care_type
        params.append(f"%{filters['care_needs']}%")
    if filters.get('location_preferences'):
        where_clauses.append("fp.location_preferences LIKE %s")
        params.append(f"%{filters['location_preferences']}%")
    if filters.get('number_of_children') is not None:
        where_clauses.append("fp.number_of_children = %s")
        params.append(filters['number_of_children'])


    if where_clauses:
        clause_str = " AND " + " AND ".join(where_clauses)
        base_query += clause_str
        count_query += clause_str

    cursor.execute(count_query, tuple(params))
    total_count_result = cursor.fetchone()
    total_count = total_count_result['total_count'] if total_count_result else 0
    
    base_query += " ORDER BY u.created_at DESC"
    offset = (page - 1) * page_size
    base_query += " LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    
    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    cursor.close()

    return results, total_count
