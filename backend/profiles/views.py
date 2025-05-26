from rest_framework import status, generics, views
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from .serializers import (
    UserSerializer, UserProfileSerializer, CaregiverProfileSerializer, 
    FamilyProfileSerializer, PhotoSerializer, AvailabilitySlotSerializer,
    MatchRequestSerializer, CaregiverMatchResponseSerializer,
    ConversationSerializer, MessageSerializer, 
    ReviewSerializer, # Added ReviewSerializer
    PublicCaregiverProfileSerializer, PublicFamilyProfileSerializer
)
from .models import User, UserProfile, CaregiverProfile, FamilyProfile, Photo, AvailabilitySlot, MatchRequest, Conversation, Message, Review # Added Review
from .permissions import (
    IsOwnerOrReadOnly, IsCaregiver, IsFamily, 
    IsTargetCaregiverForMatch, IsFamilyWhoInitiatedMatch, IsInConversation,
    IsOwnerOfReview # Added IsOwnerOfReview
)
from .filters import CaregiverProfileFilter, FamilyProfileFilter

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "message": "User registered successfully.",
            "token": token.key,
            "user_id": user.pk,
            "email": user.email,
            "role": user.role 
        }, status=status.HTTP_201_CREATED)

class LoginView(views.APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=email, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'email': user.email,
                'role': user.role,
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        try:
            user_profile = UserProfile.objects.select_related('user').get(user=user)
            if user.role == 'caregiver':
                return CaregiverProfile.objects.select_related('user_profile').get(user_profile=user_profile)
            elif user.role == 'family':
                return FamilyProfile.objects.select_related('user_profile').get(user_profile=user_profile)
            raise Http404("Role-specific profile not found.")
        except UserProfile.DoesNotExist:
            raise Http404("UserProfile not found.")
        except (CaregiverProfile.DoesNotExist, FamilyProfile.DoesNotExist):
            raise Http404("Role-specific profile not found for this user's role.")

    def get_serializer_class(self):
        user = self.request.user
        if user.role == 'caregiver':
            return CaregiverProfileSerializer
        elif user.role == 'family':
            return FamilyProfileSerializer
        raise Http404("User role not supported for this view.")

class CaregiverPublicProfileView(generics.RetrieveAPIView):
    queryset = CaregiverProfile.objects.select_related('user_profile__user').prefetch_related('photos', 'availability_slots').filter(user_profile__user__is_active=True)
    serializer_class = PublicCaregiverProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'

class FamilyPublicProfileView(generics.RetrieveAPIView):
    queryset = FamilyProfile.objects.select_related('user_profile__user').filter(user_profile__user__is_active=True)
    serializer_class = PublicFamilyProfileSerializer
    permission_classes = [AllowAny] 
    lookup_field = 'pk'

class CaregiverPhotoUploadView(generics.CreateAPIView):
    serializer_class = PhotoSerializer
    permission_classes = [IsAuthenticated, IsCaregiver]
    
    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save()

class CaregiverPhotoListView(generics.ListAPIView):
    serializer_class = PhotoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        caregiver_profile_id = self.kwargs['caregiver_profile_id']
        return Photo.objects.filter(caregiver_profile_id=caregiver_profile_id)

class CaregiverPhotoDetailView(generics.DestroyAPIView):
    serializer_class = PhotoSerializer 
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return Photo.objects.all() 

class AvailabilitySlotListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsAuthenticated, IsCaregiver]

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(caregiver_profile__user_profile__user=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}
        
    def perform_create(self, serializer):
        serializer.save()

class AvailabilitySlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsAuthenticated, IsCaregiver, IsOwnerOrReadOnly]

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(caregiver_profile__user_profile__user=self.request.user)

class CaregiverListView(generics.ListAPIView):
    queryset = CaregiverProfile.objects.select_related('user_profile__user').prefetch_related('photos', 'availability_slots').filter(user_profile__user__is_active=True)
    serializer_class = PublicCaregiverProfileSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CaregiverProfileFilter

class FamilyListView(generics.ListAPIView):
    queryset = FamilyProfile.objects.select_related('user_profile__user').filter(user_profile__user__is_active=True)
    serializer_class = PublicFamilyProfileSerializer
    permission_classes = [IsAuthenticated] 
    filter_backends = [DjangoFilterBackend]
    filterset_class = FamilyProfileFilter

# Match Request Views
class FamilyInitiateMatchView(generics.CreateAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated, IsFamily]

    def get_serializer_context(self):
        return {'request': self.request}
    
class FamilyMatchRequestListView(generics.ListAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated, IsFamily]

    def get_queryset(self):
        return MatchRequest.objects.filter(family__user_profile__user=self.request.user).select_related(
            'family__user_profile__user', 'caregiver__user_profile__user'
        ).prefetch_related('caregiver__photos', 'caregiver__availability_slots')


class CaregiverIncomingMatchListView(generics.ListAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated, IsCaregiver]

    def get_queryset(self):
        return MatchRequest.objects.filter(
            caregiver__user_profile__user=self.request.user, 
            status='pending'
        ).select_related(
            'family__user_profile__user', 'caregiver__user_profile__user'
        )

class CaregiverRespondToMatchView(generics.UpdateAPIView):
    serializer_class = CaregiverMatchResponseSerializer 
    permission_classes = [IsAuthenticated, IsCaregiver, IsTargetCaregiverForMatch]
    queryset = MatchRequest.objects.filter(status='pending') 

    def get_serializer_context(self):
        return {'request': self.request, 'match_request': self.get_object()}

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object() 
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        display_serializer = MatchRequestSerializer(instance, context=self.get_serializer_context())
        return Response(display_serializer.data)

class MutuallyMatchedListView(generics.ListAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'profile'): 
             return MatchRequest.objects.none()

        query = Q(status='accepted')
        if hasattr(user.profile, 'family_profile'):
            family_query = Q(family=user.profile.family_profile)
            query &= family_query
        elif hasattr(user.profile, 'caregiver_profile'):
            caregiver_query = Q(caregiver=user.profile.caregiver_profile)
            query &= caregiver_query
        else:
            return MatchRequest.objects.none()
            
        return MatchRequest.objects.filter(query).select_related(
            'family__user_profile__user', 'caregiver__user_profile__user'
        ).prefetch_related('caregiver__photos', 'caregiver__availability_slots', 'family__user_profile')

# Messaging System Views
class StartConversationView(generics.CreateAPIView):
    serializer_class = ConversationSerializer # Will return the new or existing conversation
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        recipient_id = request.data.get('recipient_id')
        if not recipient_id:
            return Response({"error": "recipient_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            return Response({"error": "Recipient user not found."}, status=status.HTTP_404_NOT_FOUND)

        initiator = request.user
        if initiator == recipient:
            return Response({"error": "Cannot start a conversation with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        # Check for an accepted MatchRequest between the two users
        # This logic assumes that a MatchRequest implies a family and a caregiver.
        # Adjust if conversations can be started by any two users.
        match_exists = MatchRequest.objects.filter(
            (Q(family__user_profile__user=initiator, caregiver__user_profile__user=recipient) |
             Q(family__user_profile__user=recipient, caregiver__user_profile__user=initiator)),
            status='accepted'
        ).exists()

        if not match_exists:
            return Response({"error": "An accepted match is required to start a conversation."}, status=status.HTTP_403_FORBIDDEN)

        # Check if a conversation already exists
        # A conversation is defined by its participants. Order doesn't matter.
        # This check can be complex. A simpler way is to try to fetch it.
        # For ManyToMany, Django handles the intermediate table.
        # We need to find a conversation where participants are exactly these two users.
        conversation = Conversation.objects.filter(participants=initiator).filter(participants=recipient)
        if conversation.exists():
            # If multiple, get the first one. Ideally, there should be only one.
            serializer = self.get_serializer(conversation.first(), context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Create new conversation
        new_conversation = Conversation.objects.create()
        new_conversation.participants.add(initiator, recipient)
        new_conversation.save() # Not strictly necessary after .add() but good for clarity
        
        serializer = self.get_serializer(new_conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Lists conversations for the authenticated user, ordered by the latest message (updated_at)
        return self.request.user.conversations.all().prefetch_related('participants', 'messages__sender')
    
    def get_serializer_context(self):
        return {'request': self.request}


class MessageListView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsInConversation] # IsInConversation checks object-level

    def get_conversation_object(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        # Check permission using self.check_object_permissions
        self.check_object_permissions(self.request, conversation)
        return conversation

    def get_queryset(self):
        conversation = self.get_conversation_object()
        # Mark messages as read when they are listed by a recipient
        messages_to_mark_read = conversation.messages.filter(is_read=False).exclude(sender=self.request.user)
        for message in messages_to_mark_read:
            message.is_read = True
            message.save(update_fields=['is_read'])
            
        return conversation.messages.all().select_related('sender')

    def perform_create(self, serializer):
        conversation = self.get_conversation_object()
        serializer.save(sender=self.request.user, conversation=conversation)
        # Update conversation's updated_at timestamp
        conversation.save() # This will auto-update updated_at due to auto_now=True

    def get_serializer_context(self):
        return {'request': self.request}

class MarkMessagesAsReadView(views.APIView):
    permission_classes = [IsAuthenticated, IsInConversation]

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        self.check_object_permissions(request, conversation) # Check if user is in conversation

        # Mark all messages in this conversation not sent by the current user as read
        updated_count = Message.objects.filter(
            conversation=conversation, 
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        
        return Response({'message': f'{updated_count} messages marked as read.'}, status=status.HTTP_200_OK)

# Review and Rating System Views
class SubmitReviewView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsFamily]

    def get_serializer_context(self):
        # Pass caregiver_id from URL to the serializer if needed, or handle in perform_create
        # Also pass request for user access
        context = super().get_serializer_context()
        context['request'] = self.request
        # caregiver_id is expected in the request data by ReviewSerializer's caregiver_id field
        return context

    # The ReviewSerializer's create method handles setting the family and validating the match.

class CaregiverReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        caregiver_id = self.kwargs['caregiver_id']
        caregiver_profile = get_object_or_404(CaregiverProfile, pk=caregiver_id)
        return Review.objects.filter(caregiver=caregiver_profile).select_related('family__user_profile__user')

class MyReviewForCaregiverView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsFamily, IsOwnerOfReview]
    lookup_url_kwarg = 'caregiver_id' # The URL kwarg for the caregiver_id

    def get_object(self):
        caregiver_id = self.kwargs[self.lookup_url_kwarg]
        caregiver_profile = get_object_or_404(CaregiverProfile, pk=caregiver_id)
        
        if not hasattr(self.request.user, 'profile') or not hasattr(self.request.user.profile, 'family_profile'):
            raise Http404("User is not a family member or profile is incomplete.")
        family_profile = self.request.user.profile.family_profile
        
        review = get_object_or_404(Review, caregiver=caregiver_profile, family=family_profile)
        
        # Check object permissions explicitly for this specific object
        self.check_object_permissions(self.request, review)
        return review

    def get_queryset(self):
        # This queryset is used by DRF's default mechanisms if get_object isn't overridden
        # or for certain permission checks. Since get_object is complex,
        # ensure this returns a queryset from which the object can be found.
        # However, get_object is the primary method for fetching the object here.
        if not hasattr(self.request.user, 'profile') or not hasattr(self.request.user.profile, 'family_profile'):
            return Review.objects.none()
        family_profile = self.request.user.profile.family_profile
        return Review.objects.filter(family=family_profile)

# Payment System Views
from django.conf import settings
from .paypal_utils import get_paypal_client
# Assuming TransactionSerializer is imported with other serializers
from .serializers import TransactionSerializer
from .models import Transaction # Ensure Transaction model is imported

class CreatePaymentView(views.APIView):
    permission_classes = [IsAuthenticated, IsFamily]

    def post(self, request, *args, **kwargs):
        caregiver_id = request.data.get('caregiver_id')
        amount_str = request.data.get('amount')
        currency = request.data.get('currency', 'EUR') # Default to EUR
        match_request_id = request.data.get('match_request_id')

        if not caregiver_id or not amount_str:
            return Response({"error": "Caregiver ID and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount_str) # Or Decimal for precision
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            return Response({"error": "Invalid amount specified."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            caregiver_user = User.objects.get(pk=caregiver_id, role='caregiver')
        except User.DoesNotExist:
            return Response({"error": "Caregiver user not found."}, status=status.HTTP_404_NOT_FOUND)

        initiator_user = request.user
        
        # Create local transaction record
        transaction = Transaction.objects.create(
            user_initiating_payment=initiator_user,
            user_receiving_payment=caregiver_user,
            amount=amount,
            currency=currency,
            status='pending',
            match_request_id=match_request_id
        )

        paypal = get_paypal_client()
        if not paypal:
            transaction.status = 'failed'
            transaction.save()
            return Response({"error": "PayPal SDK not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment_data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": settings.PAYPAL_RETURN_URL + f"?transaction_id={transaction.id}", # Pass our internal transaction ID
                "cancel_url": settings.PAYPAL_CANCEL_URL + f"?transaction_id={transaction.id}"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "Caregiver Service Payment",
                        "sku": f"SERVICE-{transaction.id}",
                        "price": str(amount), # Must be string
                        "currency": currency,
                        "quantity": "1"
                    }]
                },
                "amount": {
                    "total": str(amount),
                    "currency": currency
                },
                "description": f"Payment for caregiver services related to MatchRequest ID: {match_request_id if match_request_id else 'N/A'}"
            }]
        }

        try:
            payment = paypal.Payment(payment_data)
            if payment.create():
                transaction.paypal_payment_id = payment.id
                transaction.save()
                for link in payment.links:
                    if link.rel == "approval_url":
                        return Response({"approval_url": link.href}, status=status.HTTP_201_CREATED)
                return Response({"error": "No approval URL found in PayPal response."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                transaction.status = 'failed'
                transaction.save()
                # Log payment.error for more details
                return Response({"error": "PayPal payment creation failed.", "details": payment.error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            transaction.status = 'failed'
            transaction.save()
            return Response({"error": f"An exception occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecutePaymentView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs): # Changed to POST for consistency, can be GET if preferred for redirect
        payment_id = request.data.get('paymentId') # From PayPal redirect (or query params if GET)
        payer_id = request.data.get('PayerID')   # From PayPal redirect (or query params if GET)
        transaction_id = request.data.get('transaction_id') # Our internal transaction ID

        if not payment_id or not payer_id or not transaction_id:
            return Response({"error": "paymentId, PayerID, and transaction_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.get(id=transaction_id, paypal_payment_id=payment_id, user_initiating_payment=request.user)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found or mismatched."}, status=status.HTTP_404_NOT_FOUND)

        if transaction.status != 'pending':
             return Response({"error": "This payment is not pending and cannot be executed."}, status=status.HTTP_400_BAD_REQUEST)

        paypal = get_paypal_client()
        if not paypal:
            return Response({"error": "PayPal SDK not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            payment = paypal.Payment.find(payment_id)
            if payment.execute({"payer_id": payer_id}):
                transaction.status = 'completed'
                # Assuming the sale ID is the payment ID itself or within payment.transactions[0].related_resources[0].sale.id
                # This might vary based on PayPal API version and response structure.
                # For simplicity, let's assume payment.id is sufficient for now or a field from payment.transactions
                final_transaction_id = payment.transactions[0].related_resources[0].sale.id if payment.transactions and payment.transactions[0].related_resources else payment.id
                transaction.paypal_transaction_id = final_transaction_id
                transaction.save()
                return Response(TransactionSerializer(transaction).data, status=status.HTTP_200_OK)
            else:
                transaction.status = 'failed'
                transaction.save()
                return Response({"error": "PayPal payment execution failed.", "details": payment.error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            transaction.status = 'failed'
            transaction.save()
            return Response({"error": f"An exception occurred during payment execution: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancelPaymentView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs): # Changed to POST
        transaction_id = request.data.get('transaction_id') # Our internal transaction ID

        if not transaction_id:
            return Response({"error": "transaction_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.get(id=transaction_id, user_initiating_payment=request.user)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        if transaction.status == 'pending':
            transaction.status = 'cancelled' # Or 'failed' if preferred
            transaction.save()
            return Response({"message": "Payment has been cancelled."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": f"Payment cannot be cancelled. Current status: {transaction.status}"}, status=status.HTTP_400_BAD_REQUEST)


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Return transactions where the user is either the initiator or the receiver
        return Transaction.objects.filter(
            Q(user_initiating_payment=user) | Q(user_receiving_payment=user)
        ).select_related('user_initiating_payment', 'user_receiving_payment', 'match_request').order_by('-created_at')
