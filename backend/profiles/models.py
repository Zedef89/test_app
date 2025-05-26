from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('caregiver', 'Caregiver'),
        ('family', 'Family'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class CaregiverProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='caregiver_profile')
    bio = models.TextField(blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    availability_details = models.TextField(blank=True, null=True) # Legacy field, to be deprecated or used for general notes
    experience_years = models.IntegerField(blank=True, null=True)
    specializations = models.TextField(blank=True, null=True) # Consider JSONField or ManyToManyField for more structure
    certifications = models.TextField(blank=True, null=True) # Consider JSONField or ManyToManyField for more structure
    # New field for structured availability
    availability = models.JSONField(default=list, blank=True, null=True) # Stores list of dicts e.g. [{"day": "Monday", "start_time": "09:00", "end_time": "17:00"}]

    def __str__(self):
        return f"{self.user_profile.user.username} - Caregiver"

class AvailabilitySlot(models.Model):
    caregiver_profile = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='availability_slots')
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    day_of_week = models.CharField(max_length=9, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('caregiver_profile', 'day_of_week', 'start_time', 'end_time') # Prevent duplicate slots
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.caregiver_profile.user_profile.user.username} - {self.get_day_of_week_display()} {self.start_time_display} - {self.end_time_display}"

    # Add a helper to display time correctly if needed, e.g. start_time_display
    @property
    def start_time_display(self):
        return self.start_time.strftime('%H:%M')

    @property
    def end_time_display(self):
        return self.end_time.strftime('%H:%M')

class MatchRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined_by_family', 'Declined by Family'), # Family passed or withdrew
        ('declined_by_caregiver', 'Declined by Caregiver'),
    ]

    family = models.ForeignKey('FamilyProfile', on_delete=models.CASCADE, related_name='sent_match_requests')
    caregiver = models.ForeignKey('CaregiverProfile', on_delete=models.CASCADE, related_name='received_match_requests')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('family', 'caregiver', 'status') # To prevent duplicate pending requests, consider if other statuses also need this.
        # More specific constraint: only one 'pending' request from a family to a caregiver.
        constraints = [
            models.UniqueConstraint(
                fields=['family', 'caregiver'],
                condition=models.Q(status='pending'),
                name='unique_pending_request_family_caregiver'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Match request from {self.family.user_profile.user.username} to {self.caregiver.user_profile.user.username} - {self.status}"

class FamilyProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='family_profile')
    assisted_person_name = models.CharField(max_length=255, blank=True, null=True)
    assisted_person_age = models.IntegerField(blank=True, null=True)
    assisted_person_gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    assisted_person_description = models.TextField(blank=True, null=True)
    care_needs = models.TextField()
    caregiver_preferences = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user_profile.user.username} - Family"

class Photo(models.Model):
    caregiver_profile = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='photos')
    image_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.caregiver_profile.user_profile.user.username} uploaded at {self.uploaded_at}"

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Tracks the latest activity

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation between {participant_names}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} in conversation {self.conversation.id} at {self.timestamp}"

class Review(models.Model):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='reviews')
    family = models.ForeignKey(FamilyProfile, on_delete=models.CASCADE, related_name='reviews_given')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # Choices 1-5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('caregiver', 'family') # One review per family for a caregiver
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.family.user_profile.user.username} for {self.caregiver.user_profile.user.username} - {self.rating} stars"

class Transaction(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'), # Explicitly for user cancellation before execution
    ]

    user_initiating_payment = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='initiated_transactions')
    user_receiving_payment = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_transactions')
    match_request = models.ForeignKey(MatchRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR') # e.g., EUR, USD
    
    payment_method = models.CharField(max_length=50, default='paypal')
    # paypal_payment_id is the ID from PayPal when payment is created, used for execution.
    paypal_payment_id = models.CharField(max_length=100, null=True, blank=True, unique=True) 
    # paypal_transaction_id is the final sale/transaction ID after successful execution.
    paypal_transaction_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        initiator_username = self.user_initiating_payment.username if self.user_initiating_payment else "N/A"
        receiver_username = self.user_receiving_payment.username if self.user_receiving_payment else "N/A"
        return f"Transaction {self.id}: {initiator_username} to {receiver_username} - {self.amount} {self.currency} [{self.status}]"
