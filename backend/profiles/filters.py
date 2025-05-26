import django_filters
from django.db.models import Q
from .models import CaregiverProfile, FamilyProfile, AvailabilitySlot

class CaregiverProfileFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name='user_profile__city', lookup_expr='iexact')
    country = django_filters.CharFilter(field_name='user_profile__country', lookup_expr='iexact')
    max_hourly_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte')
    min_hourly_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='gte')
    min_experience_years = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    
    # Custom filter for availability by day of the week
    # This filter will find caregivers who have at least one availability slot on the specified day.
    available_on_day = django_filters.ChoiceFilter(
        label='Available on day',
        choices=AvailabilitySlot.DAY_CHOICES,
        method='filter_available_on_day'
    )

    class Meta:
        model = CaregiverProfile
        fields = ['city', 'country', 'max_hourly_rate', 'min_hourly_rate', 'min_experience_years', 'available_on_day']

    def filter_available_on_day(self, queryset, name, value):
        if value:
            # Filter caregivers that have at least one slot on the given day_of_week
            return queryset.filter(availability_slots__day_of_week=value).distinct()
        return queryset

class FamilyProfileFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name='user_profile__city', lookup_expr='iexact')
    country = django_filters.CharFilter(field_name='user_profile__country', lookup_expr='iexact')
    assisted_person_gender = django_filters.ChoiceFilter(choices=FamilyProfile.GENDER_CHOICES)
    care_needs = django_filters.CharFilter(field_name='care_needs', lookup_expr='icontains')

    class Meta:
        model = FamilyProfile
        fields = ['city', 'country', 'assisted_person_gender', 'care_needs']
