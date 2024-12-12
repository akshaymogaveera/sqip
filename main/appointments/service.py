import pytz
from main.appointments.utils import generate_time_slots
from main.service import (
    adjust_appointment_counter,
    check_category_is_active,
    check_duplicate_appointment,
    check_organization_is_active,
    get_appointment_by_id,
    get_last_counter_for_appointment,
    get_first_counter_for_appointment,
    is_slot_available
)
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta

def handle_appointment_scheduling(input_data):
    """Handle appointment validation and tracking of unscheduled appointments.

    Args:
        input_data (dict): validated data

    Returns:
        counter, msg: counter, error message
    """
    organization_id = input_data["organization"]
    category_id = input_data["category"]
    user_id = input_data["user"]

    # Get active organization and category using service layer functions
    organization = check_organization_is_active(organization_id)
    if not organization:
        return None, "Organization does not exist or is not accepting appointments."

    category = check_category_is_active(category_id, organization)
    if not category:
        return None, "Category does not exist or is not accepting appointments."

    # Check for duplicate appointment using service layer
    if check_duplicate_appointment(user_id, organization, category):
        return None, "Appointment already exists."

    # Set counter for new appointment
    counter = get_last_counter_for_appointment(organization, category)
    return counter, None


def move_appointment(current_appointment_id, previous_appointment_id=None):
    """Moves the current appointment to the position of the previous appointment."""

    with transaction.atomic():
        # Retrieve appointments
        current_appointment = get_appointment_by_id(current_appointment_id)
        previous_appointment = get_appointment_by_id(previous_appointment_id)

        # Temporarily set current appointment status to inactive
        current_appointment.status = "inactive"
        current_appointment.save()

        if previous_appointment_id is None:
            # Move to the first position
            # Increment all appointments, if moved to first.
            first_counter = get_first_counter_for_appointment(
                    current_appointment.organization, current_appointment.category
            )
            adjust_appointment_counter(
                appointment=current_appointment,
                increment=True,
                reference_counter=first_counter,
                counter_limit=current_appointment.counter,
            )
            current_appointment.counter = first_counter + 1
        elif current_appointment.counter < previous_appointment.counter:
            # Move downwards (increase counter for other appointments)
            adjust_appointment_counter(
                appointment=current_appointment,
                increment=False,
                reference_counter=current_appointment.counter,
                counter_limit=previous_appointment.counter + 1,
            )
            # Update the current appointment to updated previous appointment counter.
            previous_appointment.refresh_from_db()
            current_appointment.counter = previous_appointment.counter + 1
        elif current_appointment.counter > previous_appointment.counter:
            # Move upwards (decrease counter for other appointments)
            adjust_appointment_counter(
                appointment=current_appointment,
                increment=True,
                reference_counter=previous_appointment.counter,
                counter_limit=current_appointment.counter,
            )
            # Update the current appointment to updated previous appointment counter.
            previous_appointment.refresh_from_db()
            current_appointment.counter = previous_appointment.counter + 1

        # Reactivate and save the updated appointment
        current_appointment.status = "active"
        current_appointment.save()


def activate_appointment(appointment_id):
    """
    Activates an appointment by updating its status and counter.

    This function ensures that an appointment is eligible for activation, 
    processes scheduling, and updates the appointment status to "active" 
    if all conditions are met.

    Args:
        appointment_id (int): The unique identifier of the appointment to activate.

    Returns:
        tuple: 
            - (bool, dict or str): 
                - `True, dict`: If the appointment was successfully activated, 
                  the updated appointment details are returned as a dictionary.
                - `False, str`: If activation failed, an error message is returned.
    """
    # Fetch the appointment, bypassing any status-related restrictions
    appointment = get_appointment_by_id(appointment_id, ignore_status=True)

    # Check if the appointment is already active or scheduled
    if appointment.status == "active" or appointment.is_scheduled:
        return False, "Invalid Appointment: Already active or scheduled."

    # Convert the appointment object into a dictionary for scheduling logic
    appointment_dict = appointment.as_dict()

    # Handle scheduling, receiving the updated counter or an error message
    counter, error_message = handle_appointment_scheduling(appointment_dict)

    # If there was an error during scheduling, return a failure response
    if error_message:
        return False, f"Scheduling Error: {error_message}"

    # Update the appointment's counter and activate its status
    appointment.counter = counter
    appointment.status = "active"
    appointment.save()

    # Return success along with the updated appointment details
    return True, appointment.as_dict()


def validate_scheduled_appointment(category, scheduled_time):
    """
    Validates a scheduled appointment against category constraints.

    Args:
        category (Category): The category object containing scheduling rules.
        scheduled_time (datetime): The proposed scheduled time for the appointment.

    Raises:
        ValidationError: If any of the scheduling rules are violated.

    Returns:
        None: If all validations pass, no exceptions are raised.
    """

    # Validate time alignment with the interval
    interval_minutes = category.time_interval_per_appointment.total_seconds() // 60

    # Extract weekday, opening hours, and break hours
    weekday = scheduled_time.strftime('%A')  # e.g., 'Monday'
    opening_hours = category.opening_hours.get(weekday)
    break_hours = category.break_hours.get(weekday, [])

    # Check if opening hours for the weekday exist and are not empty
    if not opening_hours:
        raise ValidationError(f"Not accepting appointments for {weekday}.")

    # Check if within opening hours and not during break hours
    if not is_within_opening_hours(scheduled_time, opening_hours, break_hours, category.time_zone):
        raise ValidationError("Scheduled time is not within allowed hours.")

    # Validate alignment with valid start times
    validate_time_alignment(scheduled_time, interval_minutes, opening_hours, break_hours)

    # Check if the time slot is available
    if not is_slot_available(category, scheduled_time):
        raise ValidationError("The selected time slot is already taken.")



def validate_time_alignment(scheduled_time, interval_minutes, opening_hours, break_hours):
    """
    Ensures the scheduled time aligns with the category's start times.
    
    Args:
        scheduled_time (datetime): The proposed time for scheduling.
        interval_minutes (int): The interval for each appointment slot in minutes.
        opening_hours (list of lists): Opening hours ranges, e.g., [["09:00", "12:00"], ["13:00", "17:00"]].
        break_hours (list of lists): Break hours ranges, e.g., [["12:00", "13:00"]].
    
    Raises:
        ValidationError: If the time does not match one of the generated start times.
    """
    # Generate valid time slots for the day
    valid_slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    valid_start_times = [datetime.strptime(slot[0], "%H:%M").time() for slot in valid_slots]

    # Check if the scheduled time's start matches a valid slot's start
    if scheduled_time.time() not in valid_start_times:
        raise ValidationError(
            f"Scheduled time must match one of the available start times: {', '.join(slot[0] for slot in valid_slots)}."
        )

    

def is_within_opening_hours(scheduled_time, opening_hours, break_hours, category_timezone_str):
    """
    Determines if the scheduled time falls within the allowed opening hours 
    and is not during break hours for a given category.

    Args:
        scheduled_time (datetime): The time to be checked.
        opening_hours (list of lists): Opening hours ranges, e.g., [["09:00", "12:00"], ["13:00", "17:00"]].
        break_hours (list of lists): Break hours ranges, e.g., [["12:00", "13:00"]].
        category_timezone_str (str): The timezone of the category as a string, e.g., "America/New_York".

    Returns:
        bool: True if the scheduled time is within opening hours and outside break hours, False otherwise.
    """

    def is_within_ranges(time, ranges):
        """
        Helper function to check if a time falls within any of the provided time ranges.

        Args:
            time (datetime): The time to check.
            ranges (list of lists): Time ranges, e.g., [["09:00", "12:00"], ["13:00", "17:00"]].

        Returns:
            bool: True if the time is within any of the ranges, False otherwise.
        """
        for time_range in ranges:
            # Parse the start and end times for each range
            start_time = scheduled_time.replace(
                hour=int(time_range[0].split(":")[0]),
                minute=int(time_range[0].split(":")[1]),
                second=0
            )
            end_time = scheduled_time.replace(
                hour=int(time_range[1].split(":")[0]),
                minute=int(time_range[1].split(":")[1]),
                second=0
            )

            # Make sure the times are timezone-aware using the category's timezone
            category_timezone = pytz.timezone(category_timezone_str)
            if timezone.is_naive(start_time):
                start_time = category_timezone.localize(start_time)
            if timezone.is_naive(end_time):
                end_time = category_timezone.localize(end_time)

            # Check if the time is within the range
            if start_time <= time < end_time:
                return True

        return False

    # Ensure the scheduled_time is timezone-aware using the category's timezone
    category_timezone = pytz.timezone(category_timezone_str)
    if timezone.is_naive(scheduled_time):
        scheduled_time = category_timezone.localize(scheduled_time)

    # Check if the scheduled time is within the opening hours
    if not is_within_ranges(scheduled_time, opening_hours):
        return False

    # Check if the scheduled time falls within the break hours
    if is_within_ranges(scheduled_time, break_hours):
        return False

    # If both checks pass, the time is valid
    return True
