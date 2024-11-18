from main.service import (
    adjust_appointment_counter,
    check_category_is_active,
    check_duplicate_appointment,
    check_organization_is_active,
    get_appointment_by_id,
    get_last_counter_for_appointment,
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
        # Retrieve the current appointment
        current_appointment = get_appointment_by_id(current_appointment_id)
        previous_appointment = get_appointment_by_id(previous_appointment_id)

        # Temporarily set the status of the current appointment to inactive
        current_appointment.status = "inactive"
        current_appointment.save()

        # Since we are removing this appointment from current position, we will need to adjust (decrement) appointments above it.
        # Decrement all the appointments with counter > current_appointment.counter
        adjust_appointment_counter(
            current_appointment, False, current_appointment.counter
        )

        # Determine the new counter position based on the previous appointment
        # Only None if the appointment is moved to first position.
        if previous_appointment_id is None:
            # If no previous appointment, set current appointment counter to 1
            current_appointment.counter = 1
            previous_counter = 0  # Default previous counter
        else:
            # Retrieve the previous appointment
            previous_appointment = get_appointment_by_id(previous_appointment_id)
            previous_counter = previous_appointment.counter

            # The current appointment will be placed above the previous appointment.
            current_appointment.counter = (
                previous_counter + 1
            )  # Move current appointment to the new position

        # We will increment all the appointments above the previous appointments.
        # The current appointment will be above previous appointment, also the current won't be incremented as its not saved yet.
        # Move the existing appointment forward by 1
        adjust_appointment_counter(current_appointment, True, previous_counter)

        # **Step 3**: Reactivate the current appointment with the new counter
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

