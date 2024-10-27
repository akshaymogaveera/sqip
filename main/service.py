from django.core.exceptions import ObjectDoesNotExist
from .models import Appointment, Organization, Category, User
from django.db.models import Max
from django.contrib.auth import get_user_model


def check_organization_is_active(organization_id):
    """Check if the organization exists and is active."""
    try:
        return Organization.objects.get(id=organization_id, status="active")
    except Organization.DoesNotExist:
        return None

def check_category_is_active(category_id):
    """Check if the category exists and is active."""
    try:
        return Category.objects.get(id=category_id, status="active")
    except Category.DoesNotExist:
        return None
    
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
        status="active"
    ).aggregate(Max('counter'))
    
    return last_appointment['counter__max'] + 1 if last_appointment['counter__max'] else 1


def get_user_appointments(user, is_scheduled=None):
    """Retrieve active appointments for a user."""
    if is_scheduled is None:
        return Appointment.objects.filter(user=user, status="active")
    else:
        return Appointment.objects.filter(user=user, status="active", is_scheduled=is_scheduled)

def get_unscheduled_appointments_for_superuser():
    """Retrieve unscheduled active appointments for superuser."""
    return Appointment.objects.filter(is_scheduled=False, status="active").order_by("counter")

def get_authorized_organizations_for_user(user):
    """Get organizations associated with the user's groups."""
    return Organization.objects.filter(group__in=user.groups.all()).distinct()

def get_unscheduled_appointments_for_user(user):
    """Retrieve unscheduled appointments for a non-superuser."""
    authorized_organizations = get_authorized_organizations_for_user(user)
    return Appointment.objects.filter(
        is_scheduled=False,
        status="active",
        organization__in=authorized_organizations,
    ).order_by("counter")

def get_scheduled_appointments_for_superuser():
    """Retrieve scheduled active appointments for superuser."""
    return Appointment.objects.filter(is_scheduled=True, status="active").order_by("estimated_time")

def get_scheduled_appointments_for_user(user):
    """Retrieve scheduled appointments for a non-superuser."""
    authorized_organizations = get_authorized_organizations_for_user(user)
    return Appointment.objects.filter(
        is_scheduled=True,
        status="active",
        organization__in=authorized_organizations,
    ).order_by("estimated_time")
