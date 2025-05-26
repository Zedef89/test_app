from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an 'user' or 'user_profile.user' attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # This needs to be flexible based on how the object is structured.
        if hasattr(obj, 'user'): # Directly on User or UserProfile if obj is UserProfile
            return obj.user == request.user
        if hasattr(obj, 'user_profile') and hasattr(obj.user_profile, 'user'): # For CaregiverProfile, FamilyProfile
            return obj.user_profile.user == request.user
        if hasattr(obj, 'caregiver_profile') and hasattr(obj.caregiver_profile, 'user_profile') and hasattr(obj.caregiver_profile.user_profile, 'user'): # For Photo, AvailabilitySlot
             return obj.caregiver_profile.user_profile.user == request.user
        # For MatchRequest, check if the user is part of the family or caregiver profile
        if hasattr(obj, 'family') and hasattr(obj.family, 'user_profile') and hasattr(obj.family.user_profile, 'user'):
            if obj.family.user_profile.user == request.user:
                return True
        if hasattr(obj, 'caregiver') and hasattr(obj.caregiver, 'user_profile') and hasattr(obj.caregiver.user_profile, 'user'):
             if obj.caregiver.user_profile.user == request.user:
                return True
        return False

class IsCaregiver(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'caregiver'

class IsFamily(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'family'

class IsTargetCaregiverForMatch(BasePermission):
    """
    Permission to only allow the caregiver targeted by a match request to modify it.
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a MatchRequest instance
        if not (request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and hasattr(request.user.profile, 'caregiver_profile')):
            return False
        return obj.caregiver == request.user.profile.caregiver_profile

class IsFamilyWhoInitiatedMatch(BasePermission):
    """
    Permission to only allow the family who initiated a match request to modify it (e.g., withdraw).
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a MatchRequest instance
        if not (request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and hasattr(request.user.profile, 'family_profile')):
            return False
        return obj.family == request.user.profile.family_profile

class IsInConversation(BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    """
    def has_object_permission(self, request, view, obj):
        # obj is expected to be a Conversation instance for views like MessageListView
        # where the conversation is fetched first.
        # For views where obj is a Message, the check should be on obj.conversation.
        
        conversation = None
        if hasattr(obj, 'participants'): # If obj is a Conversation
            conversation = obj
        elif hasattr(obj, 'conversation'): # If obj is a Message
            conversation = obj.conversation
        else:
            # Could be an issue if the view doesn't pass a Conversation or Message object
            # or if the object structure is different than expected.
            # Fallback: try to get conversation_id from view kwargs if available.
            # This is less ideal as it tightly couples permission to URL structure.
            # For now, assume obj is either Conversation or Message.
            return False 
            
        if conversation:
            return request.user in conversation.participants.all()
        return False

class IsOwnerOfReview(BasePermission):
    """
    Custom permission to only allow the family who created the review to modify or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a Review instance.
        # Check if the user is authenticated and has a family profile.
        if not (request.user and request.user.is_authenticated and 
                hasattr(request.user, 'profile') and hasattr(request.user.profile, 'family_profile')):
            return False
        # Check if the family profile of the authenticated user is the author of the review.
        return obj.family == request.user.profile.family_profile
