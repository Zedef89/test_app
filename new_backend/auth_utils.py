# new_backend/auth_utils.py
# Will contain password hashing, token generation, and token validation functions.
from passlib.context import CryptContext

# Setup passlib context
# Schemes can be adjusted, bcrypt is a good default.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

import secrets
import datetime
# from .db_utils import get_db_connection # db_conn is passed as an argument

TOKEN_EXPIRY_DAYS = 7 # Or make this configurable

def generate_auth_token(db_conn, user_id):
    token = secrets.token_hex(32) # Generate a random 64-character hex token
    # Ensure expires_at is stored as UTC, and comparison is also UTC
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=TOKEN_EXPIRY_DAYS)
    cursor = db_conn.cursor()
    try:
        # Ensure 'auth_tokens' table and columns match your schema.sql
        cursor.execute(
            "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at)
        )
        db_conn.commit()
        return token
    except Exception as e:
        db_conn.rollback()
        raise e # Or log and return None
    finally:
        cursor.close()

def get_user_by_token(db_conn, token_str):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Optional: Clean up expired tokens first (can be a separate cron job or less frequent task)
        # cursor.execute("DELETE FROM auth_tokens WHERE expires_at < UTC_TIMESTAMP()")
        # db_conn.commit()

        # Fetch token ensuring it's not expired. UTC_TIMESTAMP() is MySQL's way to get current UTC time.
        # expires_at from DB is assumed to be stored in UTC.
        cursor.execute("SELECT user_id, expires_at FROM auth_tokens WHERE token = %s AND expires_at > UTC_TIMESTAMP()", (token_str,))
        token_data = cursor.fetchone()
        
        if token_data:
            # Check expiry again in Python, just in case of clock differences or if UTC_TIMESTAMP() behavior isn't perfectly aligned.
            # Make sure both datetimes are naive (no timezone info) or both are aware (with timezone info) for comparison.
            # datetime.datetime.utcnow() is naive. DB 'expires_at' (DATETIME type) is also naive when fetched by mysql.connector
            if token_data['expires_at'] > datetime.datetime.utcnow():
                return token_data['user_id']
            else:
                # Token is in DB but Python side considers it expired, delete it
                cursor.execute("DELETE FROM auth_tokens WHERE token = %s", (token_str,))
                db_conn.commit()
                return None # Expired
        return None # Not found or already expired based on DB query
    except Exception as e:
        # Log exception
        raise e # Or return None
    finally:
        cursor.close()

def delete_token(db_conn, token_str):
    cursor = db_conn.cursor()
    try:
        cursor.execute("DELETE FROM auth_tokens WHERE token = %s", (token_str,))
        db_conn.commit()
        return cursor.rowcount > 0 # Returns True if a token was deleted
    except Exception as e:
        db_conn.rollback()
        raise e # Or log and return False
    finally:
        cursor.close()
