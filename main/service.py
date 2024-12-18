from django.db import models
from main.models import Appointment, Organization, Category, User
from django.db.models import Max, Min
from django.utils import timezone
from pytz import timezone as pytz_timezone
from django.db.models import Q


def check_organization_is_active(organization_id):
    """Check if the organization exists and is active."""
    try:
        return Organization.objects.get(id=organization_id, status="active")
    except Organization.DoesNotExist:
        return None


def check_category_is_active(category_id, organization=None):
    """Check if the category exists and is active."""
    try:
        if organization:
            return Category.objects.get(
                id=category_id, status="active", organization=organization
            )
        else:
            return Category.objects.get(id=category_id, status="active")
    except Category.DoesNotExist:
        return None


def get_category(category_id: int):
    """Get Category.
    Raise Exception if not found.

    Args:
        id (int): category ID.
    """
    try:
        return Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return None

def are_valid_category_ids(category_ids):
    """Check if all category_ids exist and are active."""
    return Category.objects.filter(id__in=category_ids, status="active").count() == len(
        category_ids
    )


def check_user_exists(user_id):
    """Check if the user exists."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def check_duplicate_appointment(user, organization, category):
    """Check if an active appointment exists for a user with the given organization and category."""
    return Appointment.objects.filter(
        organization=organization, category=category, user=user, status="active"
    ).exists()


def get_last_counter_for_appointment(organization, category):
    """Get the last counter for an active appointment in the given organization and category."""
    last_appointment = Appointment.objects.filter(
        organization=organization,
        category=category,
        status="active",
        is_scheduled=False,
    ).aggregate(Max("counter"))

    return (
        last_appointment["counter__max"] + 1 if last_appointment["counter__max"] else 1
    )

def get_first_counter_for_appointment(organization, category):
    """
    Get the first counter for an active appointment in the given organization and category.
    Returns 0 if no appointments are found.
    """
    first_appointment = Appointment.objects.filter(
        organization=organization,
        category=category,
        status="active",
        is_scheduled=False,
    ).aggregate(Min("counter"))

    # Return the minimum counter value or 0 if none exists
    return first_appointment["counter__min"] - 1 if first_appointment["counter__min"] is not None else 0


def get_user_appointments(user, is_scheduled=None, status="active"):
    """Retrieve active appointments for a user."""
    queryset = Appointment.objects.filter(user=user, status=status)
    if is_scheduled is True:
        queryset = queryset.filter(is_scheduled=is_scheduled).order_by("scheduled_time")
    elif is_scheduled is False:
        queryset = queryset.filter(is_scheduled=is_scheduled).order_by("counter")

    return queryset


def get_unscheduled_appointments_for_superuser(category_ids=None, status="active"):
    """Retrieve unscheduled active appointments for superuser."""

    queryset = Appointment.objects.filter(is_scheduled=False, status=status)

    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)

    return queryset.order_by("counter")


def get_authorized_categories_for_user(user):
    """Get categories associated with the user's groups."""
    return Category.objects.filter(group__in=user.groups.all()).distinct()


def get_unscheduled_appointments_for_user(user, category_ids=None, status="active"):
    """Retrieve unscheduled appointments for a non-superuser, optionally filtering by category IDs."""
    authorized_categories = get_authorized_categories_for_user(user)
    # If the user has no authorized categories, return user appointments only
    if not authorized_categories:
        queryset = get_user_appointments(user=user, is_scheduled=False, status=status)

    else:
        queryset = Appointment.objects.filter(
            is_scheduled=False,
            status=status,
            category__in=authorized_categories,
        )

    # Apply category filter if category_ids are provided
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)

    return queryset.order_by("counter")


def get_scheduled_appointments_for_superuser(category_ids=None, status="active"):
    """Retrieve scheduled active appointments for superuser, optionally filtering by category IDs."""
    queryset = Appointment.objects.filter(is_scheduled=True, status=status)

    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)

    return queryset.order_by("scheduled_time")


def get_scheduled_appointments_for_user(user, category_ids=None, status="active"):
    """Retrieve scheduled appointments for a non-superuser, optionally filtering by category IDs."""
    authorized_categories = get_authorized_categories_for_user(user)
    # If the user has no authorized organizations, return user appointments only
    if not authorized_categories:
        queryset = get_user_appointments(user=user, is_scheduled=True, status=status)

    else:
        queryset = Appointment.objects.filter(
            is_scheduled=True,
            status=status,
            category__in=authorized_categories,
        )

    # Apply category filter if category_ids are provided
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)

    return queryset.order_by("scheduled_time")


def get_appointment_by_id(appointment_id, status="active", ignore_status=False):
    """Retrieve an appointment by ID.

    Args:
        appointment_id (int): The ID of the appointment to retrieve.
        status (str): Defaults to active.
        ignore_status (bool): Ignore status

    Returns:
        Appointment: The appointment instance if found, None otherwise.
    """
    try:
        if ignore_status:
            return Appointment.objects.get(id=appointment_id)
        return Appointment.objects.get(id=appointment_id, status=status)
    except Appointment.DoesNotExist:
        return None


def check_if_user_has_authorized_category_access(
    appointment_id, user, check_creator=False, ignore_status=False
):
    """Check if a user has access to a specific appointment, either by category authorization or by being the creator.

    Args:
        appointment_id (int): The ID of the appointment to check.
        user (User): The user whose access is being verified.
        check_creator (bool): If True, also check if the user is the creator of the appointment.
        ignore_status (bool): Ignore status.

    Returns:
        bool: True if the user has access to the appointment, False if unauthorized, None if not found.
    """
    # Retrieve the specific appointment by ID
    appointment = get_appointment_by_id(appointment_id, ignore_status=ignore_status)
    if not appointment:
        return None  # Appointment not found
    # If check_creator is True, verify if the user is the creator of the appointment
    if check_creator and appointment.user == user:
        return True

    # Retrieve authorized categories for the user
    authorized_categories = get_authorized_categories_for_user(user)
    # Check if the appointment's category is within the authorized categories
    return appointment.category in authorized_categories


def set_appointment_status_and_update_counter(appointment_id, status, user, ignore_status=False):
    """Set the status of an appointment and update the 'updated_by' field.
    Decrement the counter of all the appointments in the queue above it, if status is updated(except "active").

    Args:
        appointment_id (int): ID of the appointment to update.
        status (str): The new status to set for the appointment.
        user (User): The user making the update.
        ignore_status (bool): Ignore appointment status

    Returns:
        tuple: (bool, str) indicating success and a message.
    """
    # Define valid statuses based on the model's choices
    if status not in dict(Appointment.STATUS_CHOICES):
        return False, "Invalid status choice."

    # Use the helper function to retrieve the appointment
    appointment = get_appointment_by_id(appointment_id, ignore_status=ignore_status)
    if appointment is None:
        return False, "Appointment does not exist."

    # Update the status
    appointment.status = status
    appointment.updated_by = user
    appointment.save()  # Save the changes to the database

    # Decrement all appointments above it.
    if appointment.status != "active":
        adjust_appointment_counter(appointment, False, appointment.counter)

    return True, f"Appointment status updated to '{status}' successfully."


def adjust_appointment_counter(appointment, increment, reference_counter, counter_limit=None) -> None:
    """Adjusts the counter of appointments based on the specified increment or decrement action.

    Args:
        appointment: The appointment object whose counter is to be adjusted.
        increment: Boolean indicating whether to increment (True) or decrement (False) the counter.
        reference_counter: The threshold counter value used to determine which appointments to update.
        counter_limit: An optional value to further filter appointments where counter < counter_limit.
    """

    # Determine the counter adjustment operation
    counter_adjustment = models.F("counter") + (1 if increment else -1)

    # Build the base query filter
    query_filter = {
        "organization": appointment.organization.id,
        "category": appointment.category.id,
        "status": "active",
        "counter__gt": reference_counter,
        "is_scheduled": False,
    }

    # Add the counter limit condition if provided
    if counter_limit is not None:
        query_filter["counter__lt"] = counter_limit

    # Update the counter for filtered appointments
    Appointment.objects.filter(**query_filter).update(counter=counter_adjustment)


def is_slot_available(category, scheduled_time):
    """
    Checks if the proposed appointment time overlaps with any active appointments.

    Args:
        category (Category): The category object containing the scheduling rules.
        scheduled_time (datetime): The proposed scheduled time for the appointment.

    Returns:
        bool: True if the slot is available, False if the slot is taken.
    """
    # Get the appointment duration from the category
    estimated_duration = category.time_interval_per_appointment
    start_time = scheduled_time
    end_time = start_time + estimated_duration  # Add estimated duration to start time to get end time

    # Ensure that the scheduled time is timezone-aware
    category_timezone = pytz_timezone(category.time_zone)
    if timezone.is_naive(start_time):
        start_time = category_timezone.localize(start_time)
    if timezone.is_naive(end_time):
        end_time = category_timezone.localize(end_time)
        


    overlapping_appointments = Appointment.objects.filter(
        category=category,
        status="active"
    ).filter(
        Q(scheduled_time__lt=end_time) &  # Existing start time is before proposed end time
        Q(scheduled_end_time__gt=start_time)  # Existing end time is after proposed start time
    )

    return not overlapping_appointments.exists()

