from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.db.models import Avg
from .models import User, UserProfile, CaregiverProfile, FamilyProfile, Photo, AvailabilitySlot, MatchRequest, Conversation, Message, Review

# Basic User Serializer (used for displaying participant info in conversations, reviews)
class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']

class MessageSerializer(serializers.ModelSerializer):
    sender = BasicUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'timestamp', 'is_read']
        read_only_fields = ['id', 'conversation', 'sender', 'timestamp', 'is_read']

    def create(self, validated_data):
        return super().create(validated_data)

class ConversationSerializer(serializers.ModelSerializer):
    participants = BasicUserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'updated_at', 'last_message', 'unread_message_count']
        read_only_fields = ['id', 'participants', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def get_unread_message_count(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0

# Moved Summary Serializers up as they are dependencies for MatchRequestSerializer and ReviewSerializer
class PublicCaregiverProfileSummarySerializer(serializers.ModelSerializer):
    city = serializers.CharField(source='user_profile.city', read_only=True)
    country = serializers.CharField(source='user_profile.country', read_only=True)
    profile_picture_url = serializers.URLField(source='user_profile.profile_picture_url', read_only=True)
    first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)
    
    class Meta:
        model = CaregiverProfile
        fields = ['id', 'first_name', 'last_name', 'city', 'country', 'profile_picture_url', 'hourly_rate', 'experience_years']

class PublicFamilyProfileSummarySerializer(serializers.ModelSerializer):
    city = serializers.CharField(source='user_profile.city', read_only=True)
    country = serializers.CharField(source='user_profile.country', read_only=True)
    profile_picture_url = serializers.URLField(source='user_profile.profile_picture_url', read_only=True)
    first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)

    class Meta:
        model = FamilyProfile
        fields = ['id', 'first_name', 'last_name', 'city', 'country', 'profile_picture_url', 'assisted_person_name', 'care_needs']

class ReviewSerializer(serializers.ModelSerializer):
    family = PublicFamilyProfileSummarySerializer(read_only=True) 
    caregiver_id = serializers.PrimaryKeyRelatedField(
        queryset=CaregiverProfile.objects.all(), source='caregiver', write_only=True,
        help_text="ID of the caregiver being reviewed."
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ['id', 'caregiver', 'caregiver_id', 'family', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'caregiver', 'family', 'created_at', 'updated_at']

    def create(self, validated_data):
        if not hasattr(self.context['request'].user, 'profile') or not hasattr(self.context['request'].user.profile, 'family_profile'):
             raise serializers.ValidationError("User is not a family member or profile is incomplete.")
        family_profile = self.context['request'].user.profile.family_profile
        validated_data['family'] = family_profile
        
        # Check for existing review by this family for this caregiver (model already has unique_together)
        caregiver = validated_data['caregiver'] # This is set from caregiver_id by source='caregiver'
        if Review.objects.filter(family=family_profile, caregiver=caregiver).exists():
            raise serializers.ValidationError("You have already reviewed this caregiver.")
            
        # Business logic: Check for an accepted match
        match_exists = MatchRequest.objects.filter(
            family=family_profile, 
            caregiver=caregiver,
            status='accepted'
        ).exists()
        if not match_exists:
            raise serializers.ValidationError("You can only review caregivers with whom you have an accepted match.")

        return super().create(validated_data)
        
    def update(self, instance, validated_data):
        # Ensure rating is provided during update if it's being changed
        if 'rating' not in validated_data:
            validated_data['rating'] = instance.rating # Keep existing if not provided
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True},
            'username': {'read_only': True}, 
        }

    def validate_email(self, value):
        if self.instance is None and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if self.instance and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email is already in use by another user.")
        return value

    def create(self, validated_data):
        validated_data['username'] = validated_data['email'] 
        validated_data['password'] = make_password(validated_data['password'])
        role = validated_data.pop('role')
        user = User.objects.create(**validated_data)
        user_profile = UserProfile.objects.create(user=user)
        if role == 'caregiver':
            CaregiverProfile.objects.create(user_profile=user_profile)
        elif role == 'family':
            FamilyProfile.objects.create(user_profile=user_profile, care_needs="Initial setup - to be updated.")
        return user

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image_url', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def create(self, validated_data):
        if 'request' not in self.context:
             raise serializers.ValidationError("Request context is required to create a photo.")
        user = self.context['request'].user
        if not hasattr(user, 'profile') or not hasattr(user.profile, 'caregiver_profile'):
            raise serializers.ValidationError("User is not a caregiver or profile is incomplete.")
        caregiver_profile = user.profile.caregiver_profile
        validated_data['caregiver_profile'] = caregiver_profile
        return super().create(validated_data)

class UserProfileSerializer(serializers.ModelSerializer): 
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'city', 'region', 'country', 'profile_picture_url']

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'day_of_week', 'start_time', 'end_time']
        read_only_fields = ['id']

    def validate(self, data):
        if data.get('start_time') and data.get('end_time') and data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        return data
    
    def create(self, validated_data):
        if 'request' not in self.context:
             raise serializers.ValidationError("Request context is required.")
        user = self.context['request'].user
        if not hasattr(user, 'profile') or not hasattr(user.profile, 'caregiver_profile'):
            raise serializers.ValidationError("User is not a caregiver or profile is incomplete.")
        caregiver_profile = user.profile.caregiver_profile
        
        overlapping_slots = AvailabilitySlot.objects.filter(
            caregiver_profile=caregiver_profile,
            day_of_week=validated_data['day_of_week'],
            start_time__lt=validated_data['end_time'],
            end_time__gt=validated_data['start_time']
        )
        if self.instance: 
            overlapping_slots = overlapping_slots.exclude(pk=self.instance.pk)
        if overlapping_slots.exists():
            raise serializers.ValidationError("This availability slot overlaps with an existing one.")
            
        validated_data['caregiver_profile'] = caregiver_profile
        return super().create(validated_data)

    def update(self, instance, validated_data):
        caregiver_profile = instance.caregiver_profile
        overlapping_slots = AvailabilitySlot.objects.filter(
            caregiver_profile=caregiver_profile,
            day_of_week=validated_data.get('day_of_week', instance.day_of_week),
            start_time__lt=validated_data.get('end_time', instance.end_time),
            end_time__gt=validated_data.get('start_time', instance.start_time)
        ).exclude(pk=instance.pk)

        if overlapping_slots.exists():
            raise serializers.ValidationError("This availability slot overlaps with an existing one.")
        return super().update(instance, validated_data)

class CaregiverProfileSerializer(serializers.ModelSerializer): 
    user_profile = UserProfileSerializer()
    photos = PhotoSerializer(many=True, read_only=True)
    availability_slots = AvailabilitySlotSerializer(many=True, read_only=True)
    availability = serializers.JSONField(required=False)

    class Meta:
        model = CaregiverProfile
        fields = [
            'user_profile', 'bio', 'hourly_rate', 
            'availability_details', 'availability', 'experience_years', 
            'specializations', 'certifications', 'photos', 'availability_slots'
        ]

    def update(self, instance, validated_data):
        user_profile_data = validated_data.pop('user_profile', None)
        if user_profile_data:
            user_profile_serializer = UserProfileSerializer(instance.user_profile, data=user_profile_data, partial=True)
            if user_profile_serializer.is_valid(raise_exception=True):
                user_profile_serializer.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class FamilyProfileSerializer(serializers.ModelSerializer): 
    user_profile = UserProfileSerializer()

    class Meta:
        model = FamilyProfile
        fields = ['user_profile', 'assisted_person_name', 'assisted_person_age', 'assisted_person_gender', 'assisted_person_description', 'care_needs', 'caregiver_preferences']

    def update(self, instance, validated_data):
        user_profile_data = validated_data.pop('user_profile', None)
        if user_profile_data:
            user_profile_serializer = UserProfileSerializer(instance.user_profile, data=user_profile_data, partial=True)
            if user_profile_serializer.is_valid(raise_exception=True):
                user_profile_serializer.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class PublicCaregiverProfileSummarySerializer(serializers.ModelSerializer):
    city = serializers.CharField(source='user_profile.city', read_only=True)
    country = serializers.CharField(source='user_profile.country', read_only=True)
    profile_picture_url = serializers.URLField(source='user_profile.profile_picture_url', read_only=True)
    first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)
    
    class Meta:
        model = CaregiverProfile
        fields = ['id', 'first_name', 'last_name', 'city', 'country', 'profile_picture_url', 'hourly_rate', 'experience_years']

class PublicFamilyProfileSummarySerializer(serializers.ModelSerializer):
    city = serializers.CharField(source='user_profile.city', read_only=True)
    country = serializers.CharField(source='user_profile.country', read_only=True)
    profile_picture_url = serializers.URLField(source='user_profile.profile_picture_url', read_only=True)
    first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)

    class Meta:
        model = FamilyProfile
        fields = ['id', 'first_name', 'last_name', 'city', 'country', 'profile_picture_url', 'assisted_person_name', 'care_needs']


class MatchRequestSerializer(serializers.ModelSerializer):
    family = PublicFamilyProfileSummarySerializer(read_only=True)
    caregiver = PublicCaregiverProfileSummarySerializer(read_only=True)
    caregiver_id = serializers.PrimaryKeyRelatedField(
        queryset=CaregiverProfile.objects.all(), source='caregiver', write_only=True
    )

    class Meta:
        model = MatchRequest
        fields = ['id', 'family', 'caregiver', 'caregiver_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'family', 'status', 'created_at', 'updated_at'] 

    def create(self, validated_data):
        family_profile = self.context['request'].user.profile.family_profile
        validated_data['family'] = family_profile
        
        caregiver = validated_data['caregiver']
        if MatchRequest.objects.filter(family=family_profile, caregiver=caregiver, status='pending').exists():
            raise serializers.ValidationError("A pending match request to this caregiver already exists.")
            
        return super().create(validated_data)

class CaregiverMatchResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('accept', 'Accept'), ('decline', 'Decline')])

    def update(self, instance, validated_data):
        action = validated_data['action']
        if action == 'accept':
            instance.status = 'accepted'
        elif action == 'decline':
            instance.status = 'declined_by_caregiver'
        instance.save()
        return instance

class PublicCaregiverProfileSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    availability_slots = AvailabilitySlotSerializer(many=True, read_only=True)
    user_first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)
    availability = serializers.JSONField(read_only=True) 
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = CaregiverProfile
        fields = [
            'id', 'user_first_name', 'user_last_name', 
            'user_profile', 
            'bio', 'hourly_rate', 'availability_details', 'availability',
            'experience_years', 'specializations', 'certifications', 'photos', 'availability_slots',
            'average_rating', 'review_count' # Added new fields
        ]
        read_only_fields = fields

    def get_average_rating(self, obj):
        # obj is a CaregiverProfile instance
        # Calculate average from related Review objects
        # Using .aggregate(Avg('rating')) is efficient
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else None # Return None or 0.0 if no reviews

    def get_review_count(self, obj):
        return obj.reviews.count()


class PublicFamilyProfileSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)
    user_first_name = serializers.CharField(source='user_profile.user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user_profile.user.last_name', read_only=True)
    
    class Meta:
        model = FamilyProfile
        fields = [
            'id', 'user_first_name', 'user_last_name', 
            'user_profile', 
            'assisted_person_name', 'assisted_person_age', 'assisted_person_gender', 
            'assisted_person_description', 'care_needs', 'caregiver_preferences'
        ]
        read_only_fields = fields

class TransactionSerializer(serializers.ModelSerializer):
    user_initiating_payment = BasicUserSerializer(read_only=True)
    user_receiving_payment = BasicUserSerializer(read_only=True)
    # match_request can be represented by its ID or a nested serializer if needed
    match_request_id = serializers.PrimaryKeyRelatedField(
        queryset=MatchRequest.objects.all(), source='match_request', required=False, allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'user_initiating_payment', 'user_receiving_payment', 
            'match_request', 'match_request_id', 'amount', 'currency', 
            'payment_method', 'paypal_payment_id', 'paypal_transaction_id', 'status', 
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_initiating_payment', 'user_receiving_payment', 'match_request', # match_request is set via match_request_id
            'payment_method', 'paypal_payment_id', 'paypal_transaction_id', 'status', 
            'created_at', 'updated_at'
        ]
        # `amount`, `currency`, `match_request_id` are writable on creation through specific views.
        # `status` will be updated by the system based on PayPal's responses.
