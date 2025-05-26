# new_backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import datetime # Not directly used in this snippet, but good for context

from typing import Union # For response model union

from fastapi import APIRouter # New import
from typing import List # New import

from . import db_utils
from . import user_queries
from . import auth_utils
from . import profile_queries
from . import schemas
from . import caregiver_queries
from . import listing_queries
from . import matching_queries
from . import messaging_queries
from . import review_queries
from . import transaction_queries # New import
from . import paypal_utils # New import
from . import config # New import, for PayPal URLs

from fastapi import Request, Query # New imports
import math # New import

app = FastAPI()
caregiver_router = APIRouter(prefix="/api/caregivers", tags=["Caregiver Specific"])
list_router = APIRouter(tags=["Listings & Search"]) 
match_router = APIRouter(prefix="/api/matches", tags=["Matching System"]) 
messaging_router = APIRouter(prefix="/api", tags=["Messaging System"]) 
review_router = APIRouter(prefix="/api/reviews", tags=["Review System"]) 
payment_router = APIRouter(prefix="/api/payments", tags=["Payment System"]) # New Payment Router


# Dependency to get current caregiver's profile_id (from caregiver_profiles table)
async def get_current_caregiver_profile_id(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'caregiver':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a caregiver")
    
    db_conn = None
    cursor = None # Initialize cursor to None for the finally block
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (current_user['id'],))
        cg_profile = cursor.fetchone()
        if not cg_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver profile not found for this user.")
        return cg_profile['id']
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_current_caregiver_profile_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching caregiver profile ID.")
    finally:
        if cursor:
            cursor.close()
        if db_conn and db_conn.is_connected():
            db_conn.close()

# Dependency to get current family's profile_id (from family_profiles table)
async def get_current_family_profile_id(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'family':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a family member")
    
    db_conn = None
    cursor = None # Initialize cursor to None
    try:
        db_conn = db_utils.get_db_connection() # Manual DB connection
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
            
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM family_profiles WHERE user_id = %s", (current_user['id'],))
        fam_profile = cursor.fetchone()
        if not fam_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family profile not found for this user.")
        return fam_profile['id']
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_current_family_profile_id: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching family profile ID.")
    finally:
        if cursor: # Ensure cursor is closed if it was opened
            cursor.close()
        if db_conn and db_conn.is_connected(): # Close manual connection
            db_conn.close()

# Dependency to check if current user is a participant in a conversation
async def get_conversation_if_participant(
    conversation_id: int, 
    current_user: dict = Depends(get_current_user)
) -> int: # Return conversation_id for convenience if participant
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        is_participant = messaging_queries.check_user_in_conversation(db_conn, current_user['id'], conversation_id)
        if not is_participant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a participant in this conversation.")
        return conversation_id # Or True, but returning ID might be useful
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_conversation_if_participant: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error verifying conversation participation.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

# Initialize DB Pool on startup
@app.on_event("startup")
async def startup_event():
    db_utils.init_db_pool()

# Pydantic models for request bodies
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str # Consider Enum: Literal['caregiver', 'family', 'admin'] as per schema
    first_name: str | None = None
    last_name: str | None = None

class UserLogin(BaseModel):
    email: EmailStr # Or username: str. For now, supporting email only for login.
    password: str
    
class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer" # Default value for token_type
    user_id: int
    email: EmailStr
    role: str

# Security scheme for token authentication
bearer_scheme = HTTPBearer()

# Dependency to get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if db_conn is None:
            # This means init_db_pool might have failed or not been called.
            # Or get_connection itself failed.
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        token = credentials.credentials
        user_id = auth_utils.get_user_by_token(db_conn, token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # user_queries.get_user_by_id returns a dict like {'id': ..., 'email': ..., 'role': ...}
        user = user_queries.get_user_by_id(db_conn, user_id)
        if user is None: # Should ideally not happen if token is valid for a user_id that exists
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND, 
                 detail="User not found for valid token" # More specific error
            )
        return user # Returns user dict
    except HTTPException: # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Log the exception e here if you have a logger configured
        print(f"Error in get_current_user: {e}") # Basic print for now
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error in authentication")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()


@app.get("/")
async def root():
    return {"message": "Backend is running"}

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if db_conn is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        existing_user_email = user_queries.get_user_by_email(db_conn, user_data.email)
        if existing_user_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
        existing_user_username = user_queries.get_user_by_username(db_conn, user_data.username)
        if existing_user_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

        # Validate role against ENUM values in schema.sql for users.user_type
        if user_data.role not in ['caregiver', 'family', 'admin']:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role. Must be 'caregiver', 'family', or 'admin'.")

        user_id = user_queries.create_user(
            db_conn,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role, # This is 'user_type' in the DB
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        return {"message": "User registered successfully", "user_id": user_id}
    except HTTPException: # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Log the exception e
        print(f"Error in register_user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during registration.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@app.post("/api/login", response_model=TokenData)
async def login_for_access_token(form_data: UserLogin):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if db_conn is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        # get_user_by_email now returns specific fields including 'password' (hashed) and 'role' (aliased from 'user_type')
        user = user_queries.get_user_by_email(db_conn, form_data.email) 
        
        # user['password'] contains the hashed password from the DB
        if not user or not auth_utils.verify_password(form_data.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user['is_active']: # Check if user is active
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 403 Forbidden
                detail="User account is inactive."
            )

        token = auth_utils.generate_auth_token(db_conn, user['id'])
        user_queries.update_last_login(db_conn, user['id'])
        
        return TokenData(
            access_token=token,
            user_id=user['id'],
            email=user['email'], # Ensure email is EmailStr
            role=user['role']   # user['role'] is from the aliased user_type
        )
    except HTTPException: # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Log the exception e
        print(f"Error in login_for_access_token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during login.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@app.post("/api/logout")
async def logout_user(current_user: dict = Depends(get_current_user), token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if db_conn is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        token_str = token.credentials
        deleted = auth_utils.delete_token(db_conn, token_str)
        if deleted:
            return {"message": "Successfully logged out"}
        else:
            # This case might occur if token was already deleted or invalid but somehow passed get_current_user.
            # Or if the token was valid but delete_token failed for some other reason.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not log out token. It might have already been invalidated.")
    except HTTPException: # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Log the exception e
        print(f"Error in logout_user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during logout.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            
# Example protected endpoint
@app.get("/api/users/me", response_model=user_queries.get_user_by_id.__annotations__.get('return')) # Attempt to use model from query
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # current_user is the dict {'id': ..., 'email': ..., 'role': ..., 'first_name': ..., 'last_name': ..., 'is_active': ...}
    # as returned by user_queries.get_user_by_id
    return current_user

# It's good practice to define a Pydantic model for the response of /api/users/me
# For example:
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool

# And then use it:
# @app.get("/api/users/me", response_model=UserResponse)
# async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
#     return current_user
# However, Depends(get_current_user) returns a dict.
# FastAPI will validate the dict against UserResponse if UserResponse is set as response_model.

# Corrected /api/users/me with a defined Pydantic response model
class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    first_name: str | None = None
    last_name: str | None = None
    # Do not include is_active or other sensitive fields unless intended for public display via this endpoint

@app.get("/api/users/me_v2", response_model=UserPublic) # Changed path to avoid conflict, using _v2
async def read_users_me_v2(current_user: dict = Depends(get_current_user)):
    # current_user is a dict from get_user_by_id
    # It will be validated against UserPublic by FastAPI
    return current_user

# Profile Management Endpoints

@app.get("/api/profile/me", 
         response_model=Union[schemas.CaregiverProfileResponse, schemas.FamilyProfileResponse, schemas.UserBaseResponse],
         tags=["Profiles"])
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        user_id = current_user['id']
        user_role = current_user['role'] # 'role' is already correctly aliased by get_user_by_id

        profile_data = profile_queries.get_user_profile_by_id(db_conn, user_id)
        if not profile_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        if user_role == 'caregiver':
            return schemas.CaregiverProfileResponse.model_validate(profile_data)
        elif user_role == 'family':
            return schemas.FamilyProfileResponse.model_validate(profile_data)
        else: # E.g. admin or other roles that don't have a specific profile type
            return schemas.UserBaseResponse.model_validate(profile_data)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_my_profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving profile")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@app.put("/api/profile/me", 
         response_model=Union[schemas.CaregiverProfileResponse, schemas.FamilyProfileResponse, schemas.UserBaseResponse],
         tags=["Profiles"])
async def update_my_profile(profile_update_data: schemas.ProfileUpdateMe, current_user: dict = Depends(get_current_user)):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        user_id = current_user['id']
        user_role = current_user['role']

        # Use model_dump with exclude_unset=True for partial updates
        update_data_dict = profile_update_data.model_dump(exclude_unset=True)
        
        success = profile_queries.update_user_profile(db_conn, user_id, user_role, update_data_dict)
        if not success:
            # This condition might be hard to trigger if update_user_profile raises exceptions on failure
            # Consider if update_user_profile should return False or raise specific error
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")

        # Fetch the updated profile to return
        updated_profile_data = profile_queries.get_user_profile_by_id(db_conn, user_id)
        if not updated_profile_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Updated profile not found, update may have failed")

        if user_role == 'caregiver':
            return schemas.CaregiverProfileResponse.model_validate(updated_profile_data)
        elif user_role == 'family':
            return schemas.FamilyProfileResponse.model_validate(updated_profile_data)
        else:
            return schemas.UserBaseResponse.model_validate(updated_profile_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_my_profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating profile")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@app.get("/api/caregivers/{user_id}", response_model=schemas.PublicCaregiverProfileResponse, tags=["Profiles"])
async def get_public_caregiver_profile(user_id: int):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        profile_data = profile_queries.get_caregiver_public_profile(db_conn, user_id)
        if not profile_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver profile not found or user is not an active caregiver")
        
        # profile_data is a dict from the query, Pydantic will validate it
        return schemas.PublicCaregiverProfileResponse.model_validate(profile_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_public_caregiver_profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving caregiver profile")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@app.get("/api/families/{user_id}", response_model=schemas.PublicFamilyProfileResponse, tags=["Profiles"])
async def get_public_family_profile(user_id: int):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        profile_data = profile_queries.get_family_public_profile(db_conn, user_id)
        if not profile_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family profile not found or user is not an active family member")
            
        return schemas.PublicFamilyProfileResponse.model_validate(profile_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_public_family_profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving family profile")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

# Original health check from previous setup
# The one defined earlier is fine.
# The current file overwrites, so the one at the top of this file will be used.

# Include the caregiver_router in the main FastAPI app
# app.include_router(caregiver_router) # This should be at the end of the file after all routes are defined or it might not pick them up.
# For now, I will define routes and add this line at the very end.


# --- Photo Endpoints ---

@caregiver_router.post("/me/photos", response_model=schemas.PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_my_photo(
    photo_data: schemas.PhotoCreate, 
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        photo_id = caregiver_queries.add_caregiver_photo(
            db_conn, caregiver_profile_id, photo_data.image_url, photo_data.caption
        )
        if not photo_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create photo record")
            
        created_photo = caregiver_queries.get_photo_by_id(db_conn, photo_id)
        if not created_photo:
            # This should ideally not happen if add_caregiver_photo succeeded and returned an ID
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created photo")
        return schemas.PhotoResponse.model_validate(created_photo)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_my_photo: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error uploading photo")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

# Public endpoint to get photos for a specific caregiver by their user_id
@app.get("/api/caregivers/{caregiver_user_id}/photos", response_model=List[schemas.PhotoResponse], tags=["Caregiver Public"])
async def get_caregiver_photos_public(caregiver_user_id: int):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        # First, get caregiver_profile_id from caregiver_user_id (users.id)
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (caregiver_user_id,))
        cg_profile = cursor.fetchone()
        cursor.close() # Close cursor after use

        if not cg_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caregiver profile not found for this user ID")
        
        caregiver_profile_id_for_photos = cg_profile['id']
        
        photos_data = caregiver_queries.get_caregiver_photos(db_conn, caregiver_profile_id_for_photos)
        return [schemas.PhotoResponse.model_validate(photo) for photo in photos_data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_caregiver_photos_public: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving caregiver photos")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@caregiver_router.delete("/me/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_photo(
    photo_id: int, 
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        photo_to_delete = caregiver_queries.get_photo_by_id(db_conn, photo_id)
        if not photo_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
        
        if photo_to_delete['caregiver_profile_id'] != caregiver_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this photo")

        deleted = caregiver_queries.delete_caregiver_photo(db_conn, photo_id)
        if not deleted:
            # This might happen if the photo was deleted between the get and delete operations
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found or already deleted")
        
        # No content to return on successful deletion (status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_my_photo: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting photo")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

# --- Availability Slot Endpoints ---

@caregiver_router.post("/me/availability-slots", response_model=schemas.AvailabilitySlotResponse, status_code=status.HTTP_201_CREATED)
async def add_my_availability_slot(
    slot_data: schemas.AvailabilitySlotCreate,
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        # Ensure day_of_week is passed as string value of enum
        slot_id = caregiver_queries.create_availability_slot(
            db_conn, caregiver_profile_id, slot_data.day_of_week.value, slot_data.start_time, slot_data.end_time
        )
        if not slot_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create availability slot")

        created_slot = caregiver_queries.get_availability_slot_by_id(db_conn, slot_id)
        if not created_slot:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created slot")
        return schemas.AvailabilitySlotResponse.model_validate(created_slot)
    except HTTPException:
        raise
    except Exception as e: # Catch potential duplicate entry errors from DB (e.g. unique constraint violation)
        print(f"Error in add_my_availability_slot: {e}")
        # Check for specific MySQL error codes for duplicate entry if possible, e.g., e.errno == 1062
        if hasattr(e, 'errno') and e.errno == 1062: # MySQL error code for duplicate entry
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This availability slot already exists.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating availability slot")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@caregiver_router.get("/me/availability-slots", response_model=List[schemas.AvailabilitySlotResponse])
async def get_my_availability_slots(
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        slots_data = caregiver_queries.get_availability_slots_for_caregiver(db_conn, caregiver_profile_id)
        return [schemas.AvailabilitySlotResponse.model_validate(slot) for slot in slots_data]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_my_availability_slots: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving availability slots")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@caregiver_router.get("/me/availability-slots/{slot_id}", response_model=schemas.AvailabilitySlotResponse)
async def get_my_availability_slot_detail(
    slot_id: int,
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")
        
        slot_data = caregiver_queries.get_availability_slot_by_id(db_conn, slot_id)
        if not slot_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found")
        
        if slot_data['caregiver_profile_id'] != caregiver_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this availability slot")
            
        return schemas.AvailabilitySlotResponse.model_validate(slot_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_my_availability_slot_detail: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving availability slot")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@caregiver_router.put("/me/availability-slots/{slot_id}", response_model=schemas.AvailabilitySlotResponse)
async def update_my_availability_slot(
    slot_id: int,
    slot_update_data: schemas.AvailabilitySlotUpdate,
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        slot_to_update = caregiver_queries.get_availability_slot_by_id(db_conn, slot_id)
        if not slot_to_update:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found")
        
        if slot_to_update['caregiver_profile_id'] != caregiver_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this availability slot")

        # Prepare data for update: use provided values or existing ones if not provided
        update_data = slot_update_data.model_dump(exclude_unset=True)
        
        current_day = schemas.DayOfWeekEnum(slot_to_update['day_of_week'])
        day_to_update = update_data.get('day_of_week', current_day).value # .value to get string
        
        current_start_time = slot_to_update['start_time']
        start_time_to_update = update_data.get('start_time', current_start_time)
        
        current_end_time = slot_to_update['end_time']
        end_time_to_update = update_data.get('end_time', current_end_time)

        if not (day_to_update and start_time_to_update and end_time_to_update):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing fields for update")


        updated_count = caregiver_queries.update_availability_slot(
            db_conn, slot_id, day_to_update, start_time_to_update, end_time_to_update
        )
        if not updated_count:
            # This could mean the slot wasn't found or data was identical (though updated_at should change)
            # Or a concurrent modification problem.
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update availability slot")

        updated_slot = caregiver_queries.get_availability_slot_by_id(db_conn, slot_id)
        if not updated_slot: # Should not happen if update was successful
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated slot")
        return schemas.AvailabilitySlotResponse.model_validate(updated_slot)
    except HTTPException:
        raise
    except Exception as e: # Catch potential duplicate entry errors from DB
        print(f"Error in update_my_availability_slot: {e}")
        if hasattr(e, 'errno') and e.errno == 1062: # MySQL error code for duplicate entry
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This availability slot configuration already exists for another slot.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating availability slot")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@caregiver_router.delete("/me/availability-slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_availability_slot(
    slot_id: int,
    caregiver_profile_id: int = Depends(get_current_caregiver_profile_id)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        slot_to_delete = caregiver_queries.get_availability_slot_by_id(db_conn, slot_id)
        if not slot_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found")
        
        if slot_to_delete['caregiver_profile_id'] != caregiver_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this availability slot")

        deleted = caregiver_queries.delete_availability_slot(db_conn, slot_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability slot not found or already deleted")
        
        # No content to return
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_my_availability_slot: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting availability slot")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

app.include_router(caregiver_router)


# --- Listing & Search Endpoints ---

@list_router.get("/api/caregivers/", response_model=schemas.PaginatedResponse[schemas.PublicCaregiverProfileResponse])
async def list_all_caregivers(
    request: Request,
    filters: schemas.CaregiverFilterParams = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        # Use model_dump(exclude_none=True) for Pydantic v2+
        # For Pydantic v1, it would be filters.dict(exclude_none=True)
        filter_data = filters.model_dump(exclude_none=True)
        
        results, total_count = listing_queries.list_caregiver_profiles(
            db_conn, filters=filter_data, page=page, page_size=page_size
        )

        total_pages = math.ceil(total_count / page_size)
        
        next_page_url = None
        if page < total_pages:
            next_page_url = str(request.url.replace_query_params(page=page + 1))
            
        previous_page_url = None
        if page > 1:
            previous_page_url = str(request.url.replace_query_params(page=page - 1))

        # FastAPI will validate each item in results against PublicCaregiverProfileResponse
        return schemas.PaginatedResponse(
            count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            next_page_url=next_page_url,
            previous_page_url=previous_page_url,
            results=results # results are already list of dicts from query
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in list_all_caregivers: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing caregiver profiles")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

@list_router.get("/api/families/", response_model=schemas.PaginatedResponse[schemas.PublicFamilyProfileResponse])
async def list_all_families(
    request: Request,
    filters: schemas.FamilyFilterParams = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user) # Protected endpoint
):
    db_conn = None
    try:
        db_conn = db_utils.get_db_connection()
        if not db_conn:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection error")

        filter_data = filters.model_dump(exclude_none=True)
        
        results, total_count = listing_queries.list_family_profiles(
            db_conn, filters=filter_data, page=page, page_size=page_size
        )

        total_pages = math.ceil(total_count / page_size)
        
        next_page_url = None
        if page < total_pages:
            next_page_url = str(request.url.replace_query_params(page=page + 1))
            
        previous_page_url = None
        if page > 1:
            previous_page_url = str(request.url.replace_query_params(page=page - 1))

        return schemas.PaginatedResponse(
            count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            next_page_url=next_page_url,
            previous_page_url=previous_page_url,
            results=results
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in list_all_families: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing family profiles")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

app.include_router(list_router)
app.include_router(match_router) 
app.include_router(messaging_router) 
app.include_router(review_router) 
app.include_router(payment_router) # Register the new payment_router
