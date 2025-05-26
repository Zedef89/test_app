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

# --- Transaction Schemas ---
# from decimal import Decimal # Already imported
# PyEnum is already imported

class TransactionStatusEnum(str, PyEnum): # Using schema.sql values
    pending = "pending"
    completed = "completed"
    failed = "failed"
    # cancelled = "cancelled" # Not in my current schema ENUM
    refunded = "refunded"

class TransactionBase(BaseModel):
    amount: Decimal
    currency: str = "USD" # Default currency, matches my schema.sql
    user_receiving_payment_id: int # This is users.id of the recipient
    match_request_id: Optional[int] = None

class TransactionCreate(TransactionBase): # Used when initiating a payment
    # user_initiating_payment_id will be derived from the authenticated user
    pass

class TransactionUserResponse(BaseModel): # Simplified user for transaction response
    user_id: int # users.id
    username: str
    email: Optional[EmailStr] = None
    class Config: from_attributes = True

class TransactionResponse(BaseModel):
    id: int # Our internal transaction ID (transactions.id)
    user_initiating_payment: Optional[TransactionUserResponse] = None
    user_receiving_payment: Optional[TransactionUserResponse] = None
    match_request_id: Optional[int] = None
    amount: Decimal
    currency: str
    payment_method: Optional[str] = None
    paypal_payment_id: Optional[str] = None # PAYID-XXX from PayPal (transactions.paypal_payment_id)
    # paypal_transaction_id maps to transaction_reference_id in DB (SALE-XXX from PayPal)
    paypal_transaction_id: Optional[str] = None # This field will hold transactions.transaction_reference_id
    transaction_status: TransactionStatusEnum 
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
            
    @classmethod
    def from_query_result(cls, data: dict):
        init_user_data = None
        # Query aliases: init_user_id, init_username, init_email
        if data.get('init_user_id'): 
            init_user_data = TransactionUserResponse(
                user_id=data['init_user_id'], 
                username=data['init_username'], 
                email=data.get('init_email')
            )
        
        recv_user_data = None
        # Query aliases: recv_user_id, recv_username, recv_email
        if data.get('recv_user_id'):
            recv_user_data = TransactionUserResponse(
                user_id=data['recv_user_id'], 
                username=data['recv_username'], 
                email=data.get('recv_email')
            )

        return cls(
            id=data['id'], # This is transactions.id (internal_transaction_id from query)
            user_initiating_payment=init_user_data,
            user_receiving_payment=recv_user_data,
            match_request_id=data.get('match_request_id'),
            amount=data['amount'],
            currency=data['currency'],
            payment_method=data.get('payment_method'),
            paypal_payment_id=data.get('paypal_payment_id'), # PAYID-XXX
            paypal_transaction_id=data.get('transaction_reference_id'), # SALE-XXX (maps to this field)
            transaction_status=data['transaction_status'], 
            created_at=data['created_at'],
            updated_at=data.get('updated_at')
        )

class CreatePaymentRequest(BaseModel): # For POST /payments/create
    amount: Decimal 
    currency: str = "USD"
    match_request_id: int # ID of the match request this payment is for
    # user_receiving_payment_id will be derived from the match_request_id on the backend

class CreatePaymentResponse(BaseModel):
    approval_url: Optional[str] = None 
    internal_transaction_id: int     
    message: Optional[str] = None 

class ExecutePaymentRequest(BaseModel):
    paypal_payment_id: str # PAYID-XXX
    paypal_payer_id: str   # PayerID-XXX
    internal_transaction_id: int 

class CancelPaymentRequest(BaseModel): 
    internal_transaction_id: int


# --- Review Schemas ---
# Ensure HttpUrl, Field, datetime, List, Optional are imported if not already at the top.
# PyEnum is already imported for DayOfWeekEnum and MatchStatusEnum.

class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5) # Rating between 1 and 5
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    # As per task, this is for a family reviewing a caregiver.
    # The caregiver_user_id is the users.id of the caregiver being reviewed.
    # The match_request_id will be used to link the review to a specific engagement.
    caregiver_user_id: int 
    match_request_id: int # Added to link review to a specific match/job

class ReviewUpdate(BaseModel): # All fields optional for update
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewerResponse(BaseModel): # Represents the family member who wrote the review
    family_user_id: int # users.id of the family member
    family_profile_id: int # family_profiles.id
    username: str
    profile_picture_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True

class ReviewResponse(ReviewBase):
    id: int
    # caregiver_profile_id: int # The profile ID of the caregiver who was reviewed (from cp.id)
    # The reviewee_id (user_id of caregiver) is directly in reviews table.
    # My get_review_details_by_id selects cp.id AS caregiver_profile_id
    caregiver_user_id: int # Added: users.id of the caregiver reviewed (from r.reviewee_id AS caregiver_user_id)
    caregiver_profile_id: Optional[int] = None # From cp.id AS caregiver_profile_id
    
    family: ReviewerResponse # Details of the family member who wrote review
    
    review_type: str # 'family_to_caregiver' or 'caregiver_to_family' etc.
    match_request_id: Optional[int] = None
    
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
            
    @classmethod
    def from_query_result(cls, data: dict):
        # This helper maps flat query result to nested structure.
        # It expects keys from the get_review_details_by_id query.
        return cls(
            id=data['id'],
            rating=data['rating'],
            comment=data.get('comment'),
            created_at=data['created_at'],
            updated_at=data.get('updated_at'),
            caregiver_user_id=data['caregiver_user_id'], # From r.reviewee_id AS caregiver_user_id
            caregiver_profile_id=data.get('caregiver_profile_id'), # From cp.id AS caregiver_profile_id
            family=ReviewerResponse(
                family_user_id=data['family_user_id'], # From r.reviewer_id AS family_user_id
                family_profile_id=data['family_profile_id'], # From fp.id AS family_profile_id
                username=data['family_username'], # From fam_user.username
                profile_picture_url=data.get('family_profile_picture_url') # From fam_user.profile_picture
            ),
            review_type=data['review_type'],
            match_request_id=data.get('match_request_id')
        )

# PaginatedResponse[ReviewResponse] will be used for listing reviews.
# Ensure PaginatedResponse and T = TypeVar('T') are defined (they are from previous steps).

# --- Match Request Schemas ---
# Ensure HttpUrl is available if not already imported at the top
# from pydantic import HttpUrl # Already imported for PhotoBase

class MatchStatusEnum(str, PyEnum): # Using schema.sql values
    pending = 'pending'
    accepted = 'accepted'
    declined = 'declined' 
    expired = 'expired'
    completed = 'completed'
    # declined_by_family = 'declined_by_family' # Not in my current schema enum
    # declined_by_caregiver = 'declined_by_caregiver' # Not in my current schema enum


class MatchRequestCreate(BaseModel):
    caregiver_user_id: int # The users.id of the caregiver
    message_to_caregiver: Optional[str] = None
    proposed_start_date: Optional[datetime.datetime] = None
    requested_hours_per_week: Optional[int] = None


class UserInMatchResponse(BaseModel):
    user_id: int # This is users.id
    profile_id: Optional[int] = None # This is caregiver_profiles.id or family_profiles.id
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None # Using HttpUrl as per task example

    class Config:
        from_attributes = True


class MatchRequestResponse(BaseModel):
    id: int
    family: UserInMatchResponse
    caregiver: UserInMatchResponse
    status: MatchStatusEnum # Use the adapted enum
    message_to_caregiver: Optional[str] = None # Added from my schema
    proposed_start_date: Optional[datetime.datetime] = None # Added from my schema
    requested_hours_per_week: Optional[int] = None # Added from my schema
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
            
    @classmethod
    def from_query_result(cls, data: dict):
        # Helper to map flat query result to nested structure
        # Ensure data keys match the aliases from matching_queries.py
        return cls(
            id=data['id'],
            status=data['status'], # This should be 'request_status' aliased as 'status' from query
            message_to_caregiver=data.get('message_to_caregiver'),
            proposed_start_date=data.get('proposed_start_date'),
            requested_hours_per_week=data.get('requested_hours_per_week'),
            created_at=data['created_at'],
            updated_at=data.get('updated_at'),
            family=UserInMatchResponse(
                user_id=data['family_id'], 
                profile_id=data.get('family_profile_id'),
                username=data['family_username'], 
                email=data['family_email'],
                first_name=data.get('family_first_name'),
                last_name=data.get('family_last_name'),
                profile_picture_url=data.get('family_profile_picture_url')
            ),
            caregiver=UserInMatchResponse(
                user_id=data['caregiver_id'], 
                profile_id=data.get('caregiver_profile_id'),
                username=data['caregiver_username'], 
                email=data['caregiver_email'],
                first_name=data.get('caregiver_first_name'),
                last_name=data.get('caregiver_last_name'),
                profile_picture_url=data.get('caregiver_profile_picture_url')
            )
        )

class MatchUpdateRequest(BaseModel):
    status: MatchStatusEnum # Uses the adapted enum
