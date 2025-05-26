# new_backend/caregiver_queries.py
import datetime

# --- Photo Queries ---
# Assuming 'caregiver_profile_id' is passed, which links to caregiver_profiles.id
def add_caregiver_photo(db_conn, caregiver_profile_id, image_url, caption=None):
    cursor = db_conn.cursor()
    try:
        # schema.sql: photos.caregiver_profile_id
        query = "INSERT INTO photos (caregiver_profile_id, image_url, caption, uploaded_at) VALUES (%s, %s, %s, NOW())"
        cursor.execute(query, (caregiver_profile_id, image_url, caption))
        db_conn.commit()
        return cursor.lastrowid
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_caregiver_photos(db_conn, caregiver_profile_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # schema.sql: photos.caregiver_profile_id
        query = "SELECT id, caregiver_profile_id, image_url, caption, uploaded_at FROM photos WHERE caregiver_profile_id = %s ORDER BY uploaded_at DESC"
        cursor.execute(query, (caregiver_profile_id,))
        return cursor.fetchall()
    finally:
        cursor.close()

def get_photo_by_id(db_conn, photo_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        query = "SELECT id, caregiver_profile_id, image_url, caption, uploaded_at FROM photos WHERE id = %s"
        cursor.execute(query, (photo_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def delete_caregiver_photo(db_conn, photo_id): # Ownership should be checked before calling this
    cursor = db_conn.cursor()
    try:
        query = "DELETE FROM photos WHERE id = %s"
        cursor.execute(query, (photo_id,))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

# --- Availability Slot Queries ---
# Assuming 'caregiver_profile_id' is passed
def create_availability_slot(db_conn, caregiver_profile_id, day_of_week, start_time, end_time):
    cursor = db_conn.cursor()
    try:
        # schema.sql: availability_slots.caregiver_profile_id
        # schema.sql uses ENUM for day_of_week. Ensure input matches ENUM values.
        # The basic schema from task description doesn't include is_recurring or specific_date.
        # My schema.sql has: UNIQUE (caregiver_profile_id, day_of_week, start_time, end_time, specific_date)
        # For simplicity, this function assumes non-recurring, so specific_date might be NULL.
        # The table definition allows specific_date to be NULL.
        query = """
        INSERT INTO availability_slots (caregiver_profile_id, day_of_week, start_time, end_time, is_recurring, specific_date) 
        VALUES (%s, %s, %s, %s, FALSE, NULL)
        """
        cursor.execute(query, (caregiver_profile_id, day_of_week, start_time, end_time))
        db_conn.commit()
        return cursor.lastrowid
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_availability_slots_for_caregiver(db_conn, caregiver_profile_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # schema.sql: availability_slots.caregiver_profile_id
        # Querying only basic fields as per provided snippet.
        query = """
        SELECT id, caregiver_profile_id, day_of_week, start_time, end_time 
        FROM availability_slots 
        WHERE caregiver_profile_id = %s 
        ORDER BY day_of_week, start_time
        """
        # If we only want non-recurring slots created by the basic create_availability_slot:
        # query += " AND is_recurring = FALSE AND specific_date IS NULL"
        cursor.execute(query, (caregiver_profile_id,))
        return cursor.fetchall()
    finally:
        cursor.close()

def get_availability_slot_by_id(db_conn, slot_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        query = "SELECT id, caregiver_profile_id, day_of_week, start_time, end_time FROM availability_slots WHERE id = %s"
        cursor.execute(query, (slot_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def update_availability_slot(db_conn, slot_id, day_of_week, start_time, end_time): # Ownership checked before
    cursor = db_conn.cursor()
    try:
        # This update assumes the slot remains non-recurring with specific_date as NULL.
        query = "UPDATE availability_slots SET day_of_week = %s, start_time = %s, end_time = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (day_of_week, start_time, end_time, slot_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def delete_availability_slot(db_conn, slot_id): # Ownership checked before
    cursor = db_conn.cursor()
    try:
        query = "DELETE FROM availability_slots WHERE id = %s"
        cursor.execute(query, (slot_id,))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()
