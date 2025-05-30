# Configuration settings for the FastAPI application

# Database Configuration
DB_HOST = "localhost"
DB_USER = "your_db_user"
DB_PASSWORD = "your_db_password"
DB_NAME = "your_db_name"

# For JWT (alternative to simple tokens, but good to have a secret key placeholder)
# SECRET_KEY = "your-secret-key"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# PayPal Configuration (placeholder)
PAYPAL_CLIENT_ID = "your_paypal_client_id"
PAYPAL_CLIENT_SECRET = "your_paypal_client_secret"
PAYPAL_MODE = "sandbox" # or "live"
# Base URLs for redirects - the full URL will append internal_transaction_id
APP_BASE_URL = "http://localhost:8000" # Or your frontend URL
PAYPAL_RETURN_URL_PATH = "/payment/success" # Path handled by frontend
PAYPAL_CANCEL_URL_PATH = "/payment/cancel"  # Path handled by frontend

# Other application settings can be added here
# For example:
# API_KEY = "your_api_key"
