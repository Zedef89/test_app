# new_backend/schemas.py
from pydantic import BaseModel, EmailStr # HttpUrl removed as profile_picture can be path
from typing import Optional, List, Dict, Any # Literal for Enums if needed
from decimal import Decimal # For hourly_rate
import datetime

# --- Base classes with common user profile fields (adapted to schema.sql) ---
class UserProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None # Changed from region
    country: Optional[str] = None
    profile_picture: Optional[str] = None # Changed from profile_picture_url, type to str
    bio: Optional[str] = None # Added 'bio' from users table

# For updating user profiles - includes only fields that can be updated by user
class UserProfileUpdate(UserProfileBase):
    pass

# --- Caregiver specific fields for update/creation (adapted to schema.sql) ---
class CaregiverProfileSpecificsUpdate(BaseModel):
    hourly_rate: Optional[Decimal] = None
    years_of_experience: Optional[int] = None # Changed from experience_years
    skills_description: Optional[str] = None # Mapped from bio in example
    certifications: Optional[str] = None
    work_schedule_preferences: Optional[str] = None # Added
    availability_status: Optional[str] = None # Added, consider Enum: Literal['available', 'unavailable', 'booked']
    id_verified: Optional[bool] = None # Added
    background_check_status: Optional[str] = None # Added, consider Enum
    languages_spoken: Optional[str] = None # Added
    # availability_json removed, availability_details removed, specializations removed

class CaregiverProfileUpdate(UserProfileUpdate, CaregiverProfileSpecificsUpdate):
    pass

# --- Family specific fields for update/creation (adapted to schema.sql) ---
class FamilyProfileSpecificsUpdate(BaseModel):
    number_of_children: Optional[int] = None # Added
    children_ages: Optional[str] = None # Added, consider JSON/List
    specific_needs: Optional[str] = None # Added
    location_preferences: Optional[str] = None # Added
    preferred_care_type: Optional[str] = None # Added, consider Enum
    # assisted_person fields removed, care_needs and caregiver_preferences removed (as per schema adaptation)

class FamilyProfileUpdate(UserProfileUpdate, FamilyProfileSpecificsUpdate):
    pass
        
# Combined model for PUT request, to be handled based on user's role
# This model will contain all possible fields. The endpoint logic will pick relevant ones.
class ProfileUpdateMe(CaregiverProfileUpdate, FamilyProfileUpdate):
    pass

# --- Response Models (adapted to schema.sql and profile_queries.py output) ---
class UserBaseResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str # This is 'user_type' aliased as 'role' in queries
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None # Changed from region
    country: Optional[str] = None
    profile_picture: Optional[str] = None # Changed from profile_picture_url
    user_bio: Optional[str] = None # user.bio aliased as user_bio in get_user_profile_by_id
    created_at: datetime.datetime # from users table
    updated_at: Optional[datetime.datetime] = None # from users table

    class Config:
        from_attributes = True # Changed orm_mode to from_attributes for Pydantic v2

class CaregiverProfileResponse(UserBaseResponse):
    # Caregiver specific fields from caregiver_profiles table
    hourly_rate: Optional[Decimal] = None
    years_of_experience: Optional[int] = None
    skills_description: Optional[str] = None
    certifications: Optional[str] = None
    work_schedule_preferences: Optional[str] = None
    availability_status: Optional[str] = None
    id_verified: Optional[bool] = None
    background_check_status: Optional[str] = None
    languages_spoken: Optional[str] = None
    # Add photos and availability_slots if they are to be nested here in future

class FamilyProfileResponse(UserBaseResponse):
    # Family specific fields from family_profiles table
    number_of_children: Optional[int] = None
    children_ages: Optional[str] = None
    specific_needs: Optional[str] = None
    location_preferences: Optional[str] = None
    preferred_care_type: Optional[str] = None

# Union for response type can be defined in the endpoint itself using:
# from typing import Union
# response_model=Union[CaregiverProfileResponse, FamilyProfileResponse, UserBaseResponse]
# The UserBaseResponse can be a fallback if role is 'admin' or if no specific profile exists.
# Or, the endpoint can fetch the data and then decide which Pydantic model to use for serialization if needed,
# though FastAPI's response_model handles this well with Unions.

# For public profiles, we might want different (more restricted) models:
class PublicCaregiverProfileResponse(BaseModel):
    id: int
    username: str
    # email: Optional[EmailStr] = None # Typically not public
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None # Changed from state to match query alias 'u.state AS region'
    country: Optional[str] = None
    profile_picture_url: Optional[str] = None # Changed from profile_picture to match 'u.profile_picture AS profile_picture_url'
    user_bio: Optional[str] = None # from users.bio, matches 'u.bio AS user_bio'
    user_created_at: datetime.datetime # aliased from users.created_at
    
    # Caregiver specific fields from caregiver_profiles, matching aliases from list_caregiver_profiles query
    caregiver_profile_id: Optional[int] = None # Added, from 'cp.id AS caregiver_profile_id'
    hourly_rate: Optional[Decimal] = None
    experience_years: Optional[int] = None # Changed from years_of_experience to match 'cp.years_of_experience AS experience_years'
    specializations: Optional[str] = None # Changed from skills_description to match 'cp.skills_description AS specializations'
    certifications: Optional[str] = None # Matches 'cp.certifications AS certifications'
    availability_details: Optional[str] = None # Changed from availability_status to match 'cp.availability_status AS availability_details'
    # work_schedule_preferences: Optional[str] = None # This field is not directly selected with an alias in list_caregiver_profiles
    id_verified: Optional[bool] = None # Consider if this should be public, matches 'cp.id_verified'
    # background_check_status: Optional[str] = None # Typically not public, matches 'cp.background_check_status'
    languages_spoken: Optional[str] = None # Matches 'cp.languages_spoken'
    
    class Config:
        from_attributes = True

# --- Photo Schemas ---
from pydantic import HttpUrl # Ensure HttpUrl is imported
from enum import Enum as PyEnum # For DayOfWeekEnum

class PhotoBase(BaseModel):
    image_url: HttpUrl # Assuming HttpUrl is desired for public URLs. If it can be relative, str.
    caption: Optional[str] = None

class PhotoCreate(PhotoBase):
    pass

class PhotoResponse(PhotoBase):
    id: int
    caregiver_profile_id: int # Adapted to use caregiver_profile_id
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Availability Slot Schemas ---
class DayOfWeekEnum(str, PyEnum):
    monday = 'monday'
    tuesday = 'tuesday'
    wednesday = 'wednesday'
    thursday = 'thursday'
    friday = 'friday'
    saturday = 'saturday'
    sunday = 'sunday'

class AvailabilitySlotBase(BaseModel):
    day_of_week: DayOfWeekEnum
    start_time: datetime.time
    end_time: datetime.time

class AvailabilitySlotCreate(AvailabilitySlotBase):
    pass

class AvailabilitySlotResponse(AvailabilitySlotBase):
    id: int
    caregiver_profile_id: int # Adapted to use caregiver_profile_id

    class Config:
        from_attributes = True
            
class AvailabilitySlotUpdate(BaseModel): # For PUT requests, all fields optional
    day_of_week: Optional[DayOfWeekEnum] = None
    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None

class PublicFamilyProfileResponse(BaseModel):
    id: int
    username: str
    # email: Optional[EmailStr] = None # Typically not public
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None # Changed from state to match 'u.state AS region'
    country: Optional[str] = None
    profile_picture_url: Optional[str] = None # Changed from profile_picture to match 'u.profile_picture AS profile_picture_url'
    user_bio: Optional[str] = None # from users.bio, matches 'u.bio AS user_bio'
    user_created_at: datetime.datetime # aliased from users.created_at

    # Family specific fields from family_profiles, matching aliases from list_family_profiles query
    family_profile_id: Optional[int] = None # Added, from 'fp.id AS family_profile_id'
    number_of_children: Optional[int] = None # Added, from 'fp.number_of_children'
    children_ages: Optional[str] = None # Added, from 'fp.children_ages'
    specific_needs: Optional[str] = None # Added, from 'fp.specific_needs'
    location_preferences: Optional[str] = None # Added, from 'fp.location_preferences'
    care_needs: Optional[str] = None # Added, from 'fp.preferred_care_type AS care_needs'
    # assisted_person_name, assisted_person_age, assisted_person_gender, assisted_person_description, 
    # caregiver_preferences are not directly mapped from my schema in list_family_profiles query.

    class Config:
        from_attributes = True

# --- Pagination and Filter Schemas ---
from pydantic import Field # For Query parameters if needed, though FastAPI handles direct model binding for GET params
from typing import Generic, TypeVar, List, Optional # Ensure Generic, TypeVar are imported
# from decimal import Decimal # Already imported

T = TypeVar('T') # Generic type for PaginatedResponse results

class PaginationParams(BaseModel): # Not strictly needed for FastAPI Query params but good for structure
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100) # Added reasonable limits

class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    page: int
    page_size: int
    total_pages: int
    next_page_url: Optional[str] = None
    previous_page_url: Optional[str] = None
    results: List[T]

class CaregiverFilterParams(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None # Mapped from 'state' in DB query
    country: Optional[str] = None
    min_hourly_rate: Optional[Decimal] = None
    max_hourly_rate: Optional[Decimal] = None
    min_experience_years: Optional[int] = None # Mapped from 'years_of_experience' in DB query
    specializations: Optional[str] = None # Mapped from 'skills_description' in DB query
    languages_spoken: Optional[str] = None # New filter
    availability_status: Optional[str] = None # New filter, matches 'availability_details' alias for cp.availability_status
    # Consider adding id_verified if it's a filterable public attribute

class FamilyFilterParams(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None # Mapped from 'state' in DB query
    country: Optional[str] = None
    care_needs: Optional[str] = None # Mapped from 'preferred_care_type' AS care_needs in DB query
    location_preferences: Optional[str] = None # New filter
    number_of_children: Optional[int] = None # New filter
    # Consider adding specific_needs if it's a filterable public attribute
