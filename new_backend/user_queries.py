# new_backend/user_queries.py
from .auth_utils import get_password_hash
import datetime # Not strictly needed for this file based on the provided snippet, but good to keep if future date manipulations are added.

def create_user(db_conn, username, email, password, role, first_name=None, last_name=None):
    hashed_password = get_password_hash(password)
    cursor = db_conn.cursor()
    try:
        # Column name for password is 'password' as per schema.sql
        # 'user_type' is the column for role as per schema.sql
        query = """
        INSERT INTO users (username, email, password, user_type, first_name, last_name, date_joined, created_at, updated_at, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), TRUE)
        """
        cursor.execute(query, (username, email, hashed_password, role, first_name, last_name))
        db_conn.commit()
        return cursor.lastrowid # Returns the ID of the new user
    except Exception as e:
        db_conn.rollback()
        raise e # Or handle more gracefully
    finally:
        cursor.close()

def get_user_by_email(db_conn, email):
    cursor = db_conn.cursor(dictionary=True) # dictionary=True to get results as dicts
    try:
        # Select specific columns and alias user_type to role for consistency
        # Ensure 'password' column is fetched for password verification
        cursor.execute("SELECT id, username, email, password, user_type as role, first_name, last_name, is_active FROM users WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        cursor.close()

def get_user_by_username(db_conn, username):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Select specific columns and alias user_type to role
        cursor.execute("SELECT id, username, email, password, user_type as role, first_name, last_name, is_active FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        cursor.close()
        
def get_user_by_id(db_conn, user_id):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Ensure column names match schema.sql, e.g., 'user_type' for role
        cursor.execute("SELECT id, username, email, user_type as role, first_name, last_name, is_active FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def update_last_login(db_conn, user_id):
    cursor = db_conn.cursor()
    try:
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()
