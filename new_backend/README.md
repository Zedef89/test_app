# CuraMente Backend - Internal Documentation

## Overview
This document provides internal documentation for the CuraMente FastAPI backend. This backend provides API services for a platform connecting caregivers and families. It replaces a previous Django-based backend.

## Project Structure
- `main.py`: FastAPI application entry point, API routers.
- `config.py`: Configuration settings (database, PayPal, etc.). Create from `config.py.example`.
- `schema.sql`: MySQL database schema.
- `requirements.txt`: Python dependencies.
- `db_utils.py`: Database connection utilities.
- `schemas.py`: Pydantic models for request/response validation and serialization.
- `auth_utils.py`: Password hashing and token management.
- `paypal_utils.py`: (Mocked) PayPal API interaction utilities.
- Query Modules:
    - `user_queries.py`: DB operations for users.
    - `profile_queries.py`: DB operations for user profiles.
    - `caregiver_queries.py`: DB operations for caregiver-specific features.
    - `listing_queries.py`: DB operations for listing/searching profiles.
    - `matching_queries.py`: DB operations for the matching system.
    - `messaging_queries.py`: DB operations for the messaging system.
    - `review_queries.py`: DB operations for the review system.
    - `transaction_queries.py`: DB operations for transactions.

## Setup Instructions

1.  **Prerequisites:**
    - Python 3.8+
    - Pip (Python package installer)
    - MySQL Server

2.  **Clone the Repository:**
    ```bash
    # git clone ... (if applicable)
    cd path/to/new_backend # Or wherever the new_backend folder is
    ```

3.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Database Setup:**
    - Ensure your MySQL server is running.
    - Create a new database for the application (e.g., `curamente_db`).
    - Apply the schema:
      ```bash
      mysql -u your_mysql_user -p your_db_name < schema.sql
      ```
    - (Note: Replace `your_mysql_user` and `your_db_name` accordingly.)

6.  **Configuration:**
    - Copy `config.py.example` to `config.py`.
    - Edit `config.py` with your actual database credentials and PayPal API placeholders (if testing payments).
      ```python
      # config.py
      DB_HOST = "localhost"
      DB_USER = "your_db_user"
      DB_PASSWORD = "your_db_password"
      DB_NAME = "curamente_db" # Use the DB name you created

      PAYPAL_CLIENT_ID = "your_paypal_sandbox_client_id" # For testing
      PAYPAL_CLIENT_SECRET = "your_paypal_sandbox_secret"
      # ... other settings ...
      ```

## Running the Application
Use Uvicorn to run the FastAPI application:
```bash
uvicorn new_backend.main:app --reload --port 8000
```
- `--reload`: Enables auto-reload on code changes (for development).
- `--port 8000`: Runs on port 8000.

The application will be available at `http://localhost:8000`.

## API Documentation
FastAPI provides automatic interactive API documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces allow you to explore and test all API endpoints.

## Authentication
- Authentication is token-based.
- After logging in via `/api/login`, an `access_token` is returned.
- For protected endpoints, include the token in the `Authorization` header:
  `Authorization: Bearer <your_access_token>`

## Key API Dependencies
- `get_current_user`: Ensures the request is authenticated and provides the current user's basic data.
- `get_current_caregiver_profile_id`: Ensures authenticated user is a caregiver and provides their `caregiver_profiles.id`.
- `get_current_family_profile_id`: Ensures authenticated user is a family member and provides their `family_profiles.id`.
- `get_conversation_if_participant`: Ensures authenticated user is part of a specific conversation.

## (Placeholder for Frontend Integration Notes)
- If adapting the existing HTML frontend (e.g., `login.html`), JavaScript files (like `js/login.js`) are used to interact with this backend API.
- JavaScript typically uses `fetch` to make API calls, stores auth tokens in `localStorage`, and dynamically updates the HTML.

## Testing Strategy
- Manual API testing using tools like Postman or the auto-generated Swagger UI is recommended for all endpoints.
- For frontend testing, run the backend server and open HTML files in a browser.
- (Future) Implement automated unit and integration tests using FastAPI's `TestClient`.
