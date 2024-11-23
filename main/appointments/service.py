from main.service import (
    adjust_appointment_counter,
    check_category_is_active,
    check_duplicate_appointment,
    check_organization_is_active,
    get_appointment_by_id,
    get_last_counter_for_appointment,
    get_first_counter_for_appointment
)
from django.db import models, transaction


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

