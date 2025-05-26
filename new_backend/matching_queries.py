# new_backend/matching_queries.py
import datetime

# Helper function to get profile IDs (not strictly necessary here, could be done in create_match_request)
# but shows the lookup needed. For this implementation, create_match_request will do the lookups.

def create_match_request(db_conn, family_user_id: int, caregiver_user_id: int, message_to_caregiver: str = None, proposed_start_date: datetime.datetime = None, requested_hours_per_week: int = None):
    cursor = db_conn.cursor(dictionary=True) # Use dictionary cursor for fetching profile IDs
    try:
        # 1. Get family_profile_id from family_user_id
        cursor.execute("SELECT id FROM family_profiles WHERE user_id = %s", (family_user_id,))
        family_profile = cursor.fetchone()
        if not family_profile:
            raise ValueError("Family profile not found for the given family user ID.")
        family_profile_id = family_profile['id']

        # 2. Get caregiver_profile_id from caregiver_user_id
        cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (caregiver_user_id,))
        caregiver_profile = cursor.fetchone()
        if not caregiver_profile:
            raise ValueError("Caregiver profile not found for the given caregiver user ID.")
        caregiver_profile_id = caregiver_profile['id']

        # Check if a pending or accepted request already exists (using profile IDs)
        # My schema uses request_status
        query_check = "SELECT id FROM match_requests WHERE family_profile_id = %s AND caregiver_profile_id = %s AND request_status IN ('pending', 'accepted')"
        cursor.execute(query_check, (family_profile_id, caregiver_profile_id))
        if cursor.fetchone():
            raise ValueError("A pending or accepted match request already exists between these profiles.")

        # 3. Insert into match_requests using profile IDs
        # My schema uses request_status. Added other optional fields from schema.
        query = """
        INSERT INTO match_requests 
        (family_profile_id, caregiver_profile_id, request_status, message_to_caregiver, proposed_start_date, requested_hours_per_week, created_at, updated_at) 
        VALUES (%s, %s, 'pending', %s, %s, %s, NOW(), NOW())
        """
        # Close dictionary cursor and get a standard one for lastrowid if not using dictionary for insert
        cursor.close()
        cursor = db_conn.cursor()
        cursor.execute(query, (family_profile_id, caregiver_profile_id, message_to_caregiver, proposed_start_date, requested_hours_per_week))
        db_conn.commit()
        return cursor.lastrowid
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        if cursor: # cursor might be closed if an error happened before its re-assignment
            cursor.close()


def get_match_request_details_by_id(db_conn, match_request_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Adapted joins and selected fields for schema.sql
        # mr.request_status AS status
        # fam_user.profile_picture AS family_profile_picture_url (and for caregiver)
        query = """
        SELECT 
            mr.id, mr.request_status AS status, mr.message_to_caregiver, 
            mr.proposed_start_date, mr.requested_hours_per_week, mr.created_at, mr.updated_at,
            fam_user.id AS family_id, fam_user.username AS family_username, fam_user.email AS family_email, 
            fam_user.profile_picture AS family_profile_picture_url, fam_user.first_name AS family_first_name, fam_user.last_name AS family_last_name,
            fam_profile.id AS family_profile_id, 
            cg_user.id AS caregiver_id, cg_user.username AS caregiver_username, cg_user.email AS caregiver_email, 
            cg_user.profile_picture AS caregiver_profile_picture_url, cg_user.first_name AS caregiver_first_name, cg_user.last_name AS caregiver_last_name,
            cg_profile.id AS caregiver_profile_id
        FROM match_requests mr
        JOIN family_profiles fam_profile ON mr.family_profile_id = fam_profile.id
        JOIN users fam_user ON fam_profile.user_id = fam_user.id
        JOIN caregiver_profiles cg_profile ON mr.caregiver_profile_id = cg_profile.id
        JOIN users cg_user ON cg_profile.user_id = cg_user.id
        WHERE mr.id = %s
        """
        cursor.execute(query, (match_request_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
            
def get_raw_match_request_by_id(db_conn, match_request_id: int): # Simpler version for updates
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Select request_status AS status for consistency if needed, or just raw columns
        cursor.execute("SELECT id, family_profile_id, caregiver_profile_id, request_status, created_at, updated_at FROM match_requests WHERE id = %s", (match_request_id,))
        return cursor.fetchone()
    finally:
        cursor.close()


def update_match_request_status(db_conn, match_request_id: int, new_status: str):
    cursor = db_conn.cursor()
    try:
        # My schema uses request_status
        query = "UPDATE match_requests SET request_status = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (new_status, match_request_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def list_match_requests(db_conn, user_id: int, user_role: str, status_filter: str = None, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    
    # Aliases and joins adapted for schema.sql
    common_select = """
        mr.id, mr.request_status AS status, mr.created_at, mr.updated_at,
        mr.message_to_caregiver, mr.proposed_start_date, mr.requested_hours_per_week,
        fam_user.id AS family_id, fam_user.username AS family_username, fam_user.email AS family_email, 
        fam_user.profile_picture AS family_profile_picture_url, fam_user.first_name AS family_first_name, fam_user.last_name AS family_last_name,
        fam_profile.id AS family_profile_id, 
        cg_user.id AS caregiver_id, cg_user.username AS caregiver_username, cg_user.email AS caregiver_email, 
        cg_user.profile_picture AS caregiver_profile_picture_url, cg_user.first_name AS caregiver_first_name, cg_user.last_name AS caregiver_last_name,
        cg_profile.id AS caregiver_profile_id
    """
    common_joins = """
        FROM match_requests mr
        JOIN family_profiles fam_profile ON mr.family_profile_id = fam_profile.id
        JOIN users fam_user ON fam_profile.user_id = fam_user.id
        JOIN caregiver_profiles cg_profile ON mr.caregiver_profile_id = cg_profile.id
        JOIN users cg_user ON cg_profile.user_id = cg_user.id
    """
    
    base_query = f"SELECT {common_select} {common_joins}"
    count_query = f"SELECT COUNT(mr.id) as total_count {common_joins}"
    
    where_clauses = []
    params = []

    # Conditions adapted to use user_id against user_id on profiles
    if user_role == 'family':
        where_clauses.append("fam_profile.user_id = %s")
        params.append(user_id)
    elif user_role == 'caregiver':
        where_clauses.append("cg_profile.user_id = %s")
        params.append(user_id)
    elif user_role == 'mutual': 
        where_clauses.append("(fam_profile.user_id = %s OR cg_profile.user_id = %s)")
        params.extend([user_id, user_id])
        where_clauses.append("mr.request_status = 'accepted'") # Hardcoded for mutual
    
    if status_filter and user_role != 'mutual': 
        where_clauses.append("mr.request_status = %s") # Filter by request_status
        params.append(status_filter)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        count_query += " WHERE " + " AND ".join(where_clauses)
    
    cursor.execute(count_query, tuple(params))
    total_count_row = cursor.fetchone()
    total_count = total_count_row['total_count'] if total_count_row else 0
    
    base_query += " ORDER BY mr.updated_at DESC"
    offset = (page - 1) * page_size
    base_query += " LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    
    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    cursor.close()
    
    return results, total_count

# Placeholder for future functions if needed, e.g., deleting a match request
# def delete_match_request(db_conn, match_request_id: int):
#     pass
