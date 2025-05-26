from django.urls import path
from . import views # Import views to use views.ClassBasedView syntax
from .views import (
    RegisterView, LoginView, LogoutView,
    UserProfileView,
    CaregiverPublicProfileView, FamilyPublicProfileView,
    CaregiverPhotoUploadView, CaregiverPhotoListView, CaregiverPhotoDetailView,
    AvailabilitySlotListCreateView, AvailabilitySlotDetailView,
    CaregiverListView, FamilyListView
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),

    # Profile Management
    path('profile/', UserProfileView.as_view(), name='user-profile'), 

    # Public Individual Profiles (Retrieve a single profile by PK)
    path('caregivers/<int:pk>/', CaregiverPublicProfileView.as_view(), name='caregiver-public-profile-detail'),
    path('families/<int:pk>/', FamilyPublicProfileView.as_view(), name='family-public-profile-detail'),

    # Search and List Views
    path('caregivers/', CaregiverListView.as_view(), name='caregiver-list'),
    path('families/', FamilyListView.as_view(), name='family-list'),

    # Caregiver Photos
    path('caregivers/photos/upload/', CaregiverPhotoUploadView.as_view(), name='caregiver-photo-upload'),
    path('caregivers/<int:caregiver_profile_id>/photos/', CaregiverPhotoListView.as_view(), name='caregiver-photo-list'),
    path('caregivers/photos/<int:pk>/delete/', CaregiverPhotoDetailView.as_view(), name='caregiver-photo-delete'),

    # Caregiver Availability Slots
    path('caregivers/availability-slots/', AvailabilitySlotListCreateView.as_view(), name='availabilityslot-list-create'),
    path('caregivers/availability-slots/<int:pk>/', AvailabilitySlotDetailView.as_view(), name='availabilityslot-detail'),

    # Match Requests
    path('matches/initiate/', views.FamilyInitiateMatchView.as_view(), name='match-initiate'),
    path('matches/family/sent/', views.FamilyMatchRequestListView.as_view(), name='match-family-sent-list'),
    path('matches/caregiver/incoming/', views.CaregiverIncomingMatchListView.as_view(), name='match-caregiver-incoming-list'),
    path('matches/caregiver/respond/<int:pk>/', views.CaregiverRespondToMatchView.as_view(), name='match-caregiver-respond'),
    path('matches/mutual/', views.MutuallyMatchedListView.as_view(), name='match-mutual-list'),

    # Messaging System
    path('conversations/start/', views.StartConversationView.as_view(), name='conversation-start'),
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/messages/', views.MessageListView.as_view(), name='message-list-create'),
    path('conversations/<int:conversation_id>/mark-read/', views.MarkMessagesAsReadView.as_view(), name='conversation-mark-read'),

    # Review and Rating System
    # For a family to submit a review for a caregiver (caregiver_id in request body)
    path('reviews/submit/', views.SubmitReviewView.as_view(), name='review-submit'),
    # To list all reviews for a specific caregiver
    path('reviews/caregiver/<int:caregiver_id>/', views.CaregiverReviewListView.as_view(), name='review-caregiver-list'),
    # For a family to manage their own review for a specific caregiver
    path('reviews/my-review/caregiver/<int:caregiver_id>/', views.MyReviewForCaregiverView.as_view(), name='review-my-review-for-caregiver'),

    # Payment System
    path('payments/create/', views.CreatePaymentView.as_view(), name='payment-create'),
    path('payments/execute/', views.ExecutePaymentView.as_view(), name='payment-execute'), # Expects paymentId, PayerID, transaction_id in request body
    path('payments/cancel/', views.CancelPaymentView.as_view(), name='payment-cancel'),   # Expects transaction_id in request body
    path('payments/history/', views.TransactionListView.as_view(), name='payment-history'),
]
