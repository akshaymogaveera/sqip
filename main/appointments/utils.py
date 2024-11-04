
from main.models import Appointment
from django.db import models

from main.service import get_appointment_by_id

def update_appointment(appointment_id, status, increment=False, current_counter=None):

    appointment = get_appointment_by_id(appointment_id)
    appointment.status = status
    appointment.save()

    current_counter = appointment.counter if current_counter is None else current_counter

    # Fetch organization_id and category_id from current_appointment
    organization_id = appointment.organization.id
    category_id = appointment.category.id

    if increment:
        counter = models.F('counter') + 1
    else:
        counter = models.F('counter') - 1


    # Update the counter for active appointments created after the threshold counter
    Appointment.objects.filter(
        organization=organization_id,
        category=category_id,
        status="active",
        counter__gt=current_counter,
        scheduled=False
    ).update(counter=counter)
