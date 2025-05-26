# new_backend/review_queries.py
import datetime

# This helper remains useful for checks involving profile tables (like match_requests)
def get_profile_id_from_user_id(db_conn, user_id: int, role: str) -> int | None:
    cursor = db_conn.cursor(dictionary=True)
    try:
        if role == 'caregiver':
            cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (user_id,))
        elif role == 'family':
            cursor.execute("SELECT id FROM family_profiles WHERE user_id = %s", (user_id,))
        else:
            return None
        profile = cursor.fetchone()
        return profile['id'] if profile else None
    finally:
        cursor.close()

def check_if_family_can_review_caregiver(db_conn, family_profile_id: int, caregiver_profile_id: int, match_request_id_optional: int = None) -> bool:
    """
    Checks for an accepted match between family_profile_id and caregiver_profile_id.
    If match_request_id_optional is provided, it also ensures this specific match is the one being reviewed.
    """
    cursor = db_conn.cursor(dictionary=True)
    try:
        # My match_requests table uses profile_ids directly.
        # My reviews table has a 'match_request_id' which is UNIQUE.
        query = """
        SELECT mr.id 
        FROM match_requests mr
        WHERE mr.request_status = 'accepted' AND 
              mr.family_profile_id = %s AND mr.caregiver_profile_id = %s
        """
        params = [family_profile_id, caregiver_profile_id]
        if match_request_id_optional:
            query += " AND mr.id = %s"
            params.append(match_request_id_optional)
        
        query += " LIMIT 1"
        cursor.execute(query, tuple(params))
        return cursor.fetchone() is not None
    finally:
        cursor.close()

# Adapted to use reviewer_user_id and reviewee_user_id, and review_type
def create_review(db_conn, reviewer_user_id: int, reviewee_user_id: int, rating: int, comment: str = None, review_type: str = 'family_to_caregiver', match_request_id: int = None):
    cursor = db_conn.cursor()
    try:
        # My reviews table stores reviewer_id (user_id) and reviewee_id (user_id)
        # It also has match_request_id (UNIQUE) and review_type
        query = """
        INSERT INTO reviews (reviewer_id, reviewee_id, rating, comment, review_type, match_request_id, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        cursor.execute(query, (reviewer_user_id, reviewee_user_id, rating, comment, review_type, match_request_id))
        db_conn.commit()
        return cursor.lastrowid
    except Exception as e: 
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

# Adapted to reflect my reviews schema and provide data for ReviewResponse
def get_review_details_by_id(db_conn, review_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # My reviews table has reviewer_id (family user) and reviewee_id (caregiver user for family_to_caregiver reviews)
        # The Pydantic ReviewResponse expects caregiver_profile_id and a nested family object with family_profile_id.
        # This requires joining with profile tables.
        query = """
        SELECT 
            r.id, r.rating, r.comment, r.created_at, r.updated_at, r.review_type, r.match_request_id,
            r.reviewee_id AS caregiver_user_id, -- Assuming reviewee is caregiver for 'family_to_caregiver'
            cp.id AS caregiver_profile_id,      -- Fetched caregiver_profile_id
            r.reviewer_id AS family_user_id,    -- family user who wrote the review
            fp.id AS family_profile_id,         -- Fetched family_profile_id
            fam_user.username AS family_username, 
            fam_user.profile_picture AS family_profile_picture_url
        FROM reviews r
        JOIN users fam_user ON r.reviewer_id = fam_user.id
        LEFT JOIN family_profiles fp ON r.reviewer_id = fp.user_id  -- To get family_profile_id
        LEFT JOIN caregiver_profiles cp ON r.reviewee_id = cp.user_id -- To get caregiver_profile_id
        WHERE r.id = %s 
        """ 
        # This query assumes review_type='family_to_caregiver' for the aliasing of caregiver_user_id.
        # If review_type can be 'caregiver_to_family', then reviewee_id would be family_user_id.
        # For simplicity, this detail query is generic; the specific use in endpoints should ensure context.
        cursor.execute(query, (review_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
            
def get_raw_review_by_id(db_conn, review_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Returns raw columns including reviewer_id, reviewee_id, review_type
        cursor.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

# Adapted for reviewee_user_id (caregiver's user_id)
def get_reviews_for_caregiver(db_conn, caregiver_user_id: int, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Filters by reviewee_id and review_type
        count_query = """
        SELECT COUNT(id) as total_count FROM reviews 
        WHERE reviewee_id = %s AND review_type = 'family_to_caregiver'
        """
        cursor.execute(count_query, (caregiver_user_id,))
        total_count_result = cursor.fetchone()
        total_count = total_count_result['total_count'] if total_count_result else 0

        offset = (page - 1) * page_size
        query_ids = """
        SELECT id FROM reviews 
        WHERE reviewee_id = %s AND review_type = 'family_to_caregiver' 
        ORDER BY created_at DESC LIMIT %s OFFSET %s
        """
        cursor.execute(query_ids, (caregiver_user_id, page_size, offset))
        review_ids_data = cursor.fetchall()
        
        detailed_reviews = []
        if review_ids_data:
            for row in review_ids_data:
                # get_review_details_by_id should be able to handle any review_id correctly
                review_detail = get_review_details_by_id(db_conn, row['id'])
                if review_detail:
                    detailed_reviews.append(review_detail)
        
        return detailed_reviews, total_count
    finally:
        cursor.close()

# Adapted for family_user_id and caregiver_user_id
def get_review_by_family_for_caregiver(db_conn, family_user_id: int, caregiver_user_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Query using reviewer_id (family_user_id) and reviewee_id (caregiver_user_id)
        query = """
        SELECT id FROM reviews 
        WHERE reviewer_id = %s AND reviewee_id = %s AND review_type = 'family_to_caregiver' 
        LIMIT 1
        """
        cursor.execute(query, (family_user_id, caregiver_user_id))
        review_id_row = cursor.fetchone()
        
        if review_id_row:
            # Fetch full details using the generic detail query
            return get_review_details_by_id(db_conn, review_id_row['id'])
        return None
    finally:
        cursor.close()

def update_review(db_conn, review_id: int, rating: int, comment: str = None):
    cursor = db_conn.cursor()
    try:
        query = "UPDATE reviews SET rating = %s, comment = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (rating, comment, review_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def delete_review(db_conn, review_id: int):
    cursor = db_conn.cursor()
    try:
        query = "DELETE FROM reviews WHERE id = %s"
        cursor.execute(query, (review_id,))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()
