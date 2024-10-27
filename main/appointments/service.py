from main.service import check_category_is_active, check_duplicate_appointment, check_organization_is_active, get_last_counter_for_appointment

def handle_appointment_scheduling(input_data):
    organization_id = input_data['organization']
    category_id = input_data['category']
    user_id = input_data['user']

    # Get active organization and category using service layer functions
    organization = check_organization_is_active(organization_id)
    if not organization:
        return None, "Organization does not exist or is not accepting appointments."

    category = check_category_is_active(category_id)
    if not category:
        return None, "Category does not exist or is not accepting appointments."

    # Check for duplicate appointment using service layer
    if check_duplicate_appointment(user_id, organization, category):
        return None, "Appointment already exists."

    # Set counter for new appointment
    counter = get_last_counter_for_appointment(organization, category)
    return counter, None