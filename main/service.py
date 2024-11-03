from django.core.exceptions import ObjectDoesNotExist
from main.models import Appointment, Organization, Category, User
from django.db.models import Max
from django.contrib.auth import get_user_model


def check_organization_is_active(organization_id):
    """Check if the organization exists and is active."""
    try:
        return Organization.objects.get(id=organization_id, status="active")
    except Organization.DoesNotExist:
        return None

def check_category_is_active(category_id, organization = None):
    """Check if the category exists and is active."""
    try:
        if organization:
            return Category.objects.get(id=category_id, status="active", organization=organization)
        else:
            return Category.objects.get(id=category_id, status="active")
    except Category.DoesNotExist:
        return None
    
def are_valid_category_ids(category_ids):
    """Check if all category_ids exist and are active."""
    return Category.objects.filter(id__in=category_ids, status='active').count() == len(category_ids)

    
def check_user_exists(user_id):
    """Check if the user exists."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

def check_duplicate_appointment(user, organization, category):
    """Check if an active appointment exists for a user with the given organization and category."""
    return Appointment.objects.filter(
        organization=organization, 
        category=category, 
        user=user, 
        status="active"
    ).exists()

def get_last_counter_for_appointment(organization, category):
    """Get the last counter for an active appointment in the given organization and category."""
    last_appointment = Appointment.objects.filter(
        organization=organization,
        category=category,
        status="active",
        is_scheduled=False
    ).aggregate(Max('counter'))
    
    return last_appointment['counter__max'] + 1 if last_appointment['counter__max'] else 1


def get_user_appointments(user, is_scheduled=None):
    """Retrieve active appointments for a user."""
    queryset = Appointment.objects.filter(user=user, status="active")
    if is_scheduled is True:
        queryset = queryset.filter(is_scheduled=is_scheduled).order_by("estimated_time")
    elif is_scheduled is False:
        queryset = queryset.filter(is_scheduled=is_scheduled).order_by("counter")
    
    return queryset

def get_unscheduled_appointments_for_superuser(category_ids = None):
    """Retrieve unscheduled active appointments for superuser."""

    queryset = Appointment.objects.filter(is_scheduled=False, status="active")
    
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)
    
    return queryset.order_by("counter")

def get_authorized_categories_for_user(user):
    """Get categories associated with the user's groups."""
    return Category.objects.filter(group__in=user.groups.all()).distinct()

def get_unscheduled_appointments_for_user(user, category_ids=None):
    """Retrieve unscheduled appointments for a non-superuser, optionally filtering by category IDs."""
    authorized_categories = get_authorized_categories_for_user(user)
    # If the user has no authorized organizations, return their appointments only
    if not authorized_categories:
        queryset = get_user_appointments(user=user, is_scheduled=False)
    
    else:
        queryset = Appointment.objects.filter(
            is_scheduled=False,
            status="active",
            category__in=authorized_categories,
        )

    # Apply category filter if category_ids are provided
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)
    
    return queryset.order_by("counter")



def get_scheduled_appointments_for_superuser(category_ids=None):
    """Retrieve scheduled active appointments for superuser, optionally filtering by category IDs."""
    queryset = Appointment.objects.filter(is_scheduled=True, status="active")
    
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)
    
    return queryset.order_by("estimated_time")


def get_scheduled_appointments_for_user(user, category_ids=None):
    """Retrieve scheduled appointments for a non-superuser, optionally filtering by category IDs."""
    authorized_categories = get_authorized_categories_for_user(user)
    # If the user has no authorized organizations, return their appointments only
    if not authorized_categories:
        queryset = get_user_appointments(user=user, is_scheduled=True)
    
    else:
        queryset = Appointment.objects.filter(
            is_scheduled=True,
            status="active",
            category__in=authorized_categories,
        )

    # Apply category filter if category_ids are provided
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)
    
    return queryset.order_by("estimated_time")

