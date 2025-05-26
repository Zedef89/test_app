import mysql.connector
from mysql.connector import pooling
from . import config # Assuming config.py is in the same directory

# Global connection pool (recommended)
db_pool = None

def init_db_pool():
    global db_pool
    try:
        db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=5, # Adjust as needed
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        print("Database connection pool initialized.")
    except mysql.connector.Error as err:
        print(f"Error initializing database pool: {err}")
        # Potentially exit or raise the error if DB is critical at startup
        db_pool = None # Ensure it's None if failed

def get_db_connection():
    if not db_pool:
        # This could happen if init_db_pool failed or wasn't called
        # Depending on strategy, you could try to init here or raise an error
        # For now, let's assume init_db_pool is called at app startup
        raise Exception("Database pool not initialized. Call init_db_pool() at application startup.")
    
    try:
        # Get a connection from the pool
        conn = db_pool.get_connection()
        return conn
    except mysql.connector.Error as err:
        print(f"Error getting connection from pool: {err}")
        return None # Or raise an error

# It's good practice to call init_db_pool() when the FastAPI app starts.
# This can be done in main.py using FastAPI's startup events.
