from datetime import datetime, timedelta
from django.utils.timezone import now
from main.exceptions import UnauthorizedAccessException
from main.service import (
    check_category_is_active,
    check_if_user_has_authorized_category_access,
    check_organization_is_active,
    check_user_exists,
    are_valid_category_ids,
    get_appointment_by_id,
    get_authorized_categories_for_user,
)
from rest_framework import serializers, status
from main.models import Appointment, Category, Organization
from main.appointments.service import validate_scheduled_appointment
from main.utils import convert_time_to_utc


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class ValidateAppointmentInput(serializers.Serializer):
    organization = serializers.IntegerField(required=True)
    category = serializers.IntegerField(required=True)
    user = serializers.IntegerField(required=True)

    def validate_organization(self, value):
        """Validate if the organization exists and is active using the service layer."""
        organization = check_organization_is_active(value)
        if not organization:
            raise serializers.ValidationError(
                "Organization does not exist or is not active."
            )
        return value

    def validate_category(self, value):
        """Validate if the category exists and is active using the service layer."""
        category = check_category_is_active(value)

        if not category:
            raise serializers.ValidationError(
                "Category does not exist or is not active."
            )
        return value

    def validate_user(self, value):
        """Validate if the user exists and is allowed to create the appointment."""
        user = check_user_exists(value)
        if not user:
            raise serializers.ValidationError("User does not exist.")
        return value

    def validate(self, attrs):
        """Additional validations that depend on multiple fields."""

        request_user = self.context["request"].user  # The user making the request
        user_id = attrs.get("user")
        category_id = attrs.get("category")

        authorized_category_ids = get_authorized_categories_for_user(
            request_user
        ).values_list("id", flat=True)
        is_user_authorized_for_category = category_id in authorized_category_ids

        if (
            request_user.id != user_id
            and not request_user.is_staff
            and not request_user.is_superuser
            and not is_user_authorized_for_category
        ):
            raise UnauthorizedAccessException(
                detail="Unauthorized to access this appointment."
            )

        return attrs


class MakeAppointmentSerializer(serializers.ModelSerializer):
    def validate(self, data):
        # Add custom validation for the serializer as a whole
        # For example, you can check if 'organization' is present and valid

        return data

    class Meta:
        model = Appointment
        fields = [
            "id",
            "user",
            "category",
            "type",
            "organization",
            "status",
            "date_created",
            "counter",
            "is_scheduled",
            "estimated_time",
        ]

class AppointmentListValidate(serializers.Serializer):
    status = serializers.ChoiceField(choices=Appointment.STATUS_CHOICES, required=False)
    type = serializers.ChoiceField(choices=["unscheduled", "scheduled", "all"], required=False)

    def validate(self, attrs):
        """Additional validations that depend on multiple fields."""
        
        status = attrs.get("status")
        type = attrs.get("type")

        # Validate the status field
        if status and status not in dict(Appointment.STATUS_CHOICES).keys():
            raise serializers.ValidationError(f"Invalid status: {status}")

        # Validate the status_type field
        if type and type not in ["unscheduled", "scheduled", "all"]:
            raise serializers.ValidationError(f"Invalid status type: {type}")

        return attrs

class AppointmentListQueryParamsSerializer(serializers.Serializer):
    category_id = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
    status = serializers.ChoiceField(
        choices=Appointment.STATUS_CHOICES, required=False
    )

    def validate_category_id(self, value):
        """Validate category id.

        Raises:
            serializers.ValidationError
        """
        # Validate the list length
        if not value:
            return value
        if len(value) > 10:
            raise serializers.ValidationError(
                "You can only filter by a maximum of 10 category IDs."
            )

        # Validate category IDs using the service method
        if not are_valid_category_ids(value):
            raise serializers.ValidationError("One or more category IDs are invalid.")

        return value

    def validate_status(self, value):
        """Validate Status"""
        # If a status is provided, check it's a valid status choice
        if value and value not in dict(Appointment.STATUS_CHOICES).keys():
            raise serializers.ValidationError(f"Invalid status: {value}")
        return value


class BaseAppointmentIDValidatorSerializer(serializers.Serializer):
    """Serializer to validate if an appointment with a given ID exists and if the user has access to it."""

    appointment_id = serializers.IntegerField()

    def validate(self, attrs):
        """Validate the appointment ID and check user authorization."""
        request = self.context.get("request")
        check_creator = self.context.get("check_creator")
        user = request.user
        appointment_id = attrs.get("appointment_id")

        # if user is admin.
        if user.is_staff or user.is_superuser:
            return attrs

        response = check_if_user_has_authorized_category_access(
            appointment_id, user, check_creator, ignore_status=True
        )
        if response is None:
            raise serializers.ValidationError(
                "Appointment with this ID does not exist."
            )
        elif response is False:
            raise UnauthorizedAccessException(
                detail="Unauthorized to access this appointment."
            )
        return attrs  # Proceed if the user is authorized and appointment exists


class AppointmentIDValidatorSerializer(BaseAppointmentIDValidatorSerializer):
    """Serializer to validate appointment_id with Base logic."""

    pass  # Inherits everything from BaseAppointmentIDValidatorSerializer


class MoveAppointmentIDValidatorSerializer(BaseAppointmentIDValidatorSerializer):
    """Serializer for moving an appointment, includes optional previous_appointment_id."""

    previous_appointment_id = serializers.IntegerField(allow_null=True)

    def validate(self, attrs):
        """Extend validation to optionally include previous_appointment_id."""
        # Call parent validation
        attrs = super().validate(attrs)

        # Custom validation for previous_appointment_id
        previous_appointment_id = attrs.get("previous_appointment_id")

        if previous_appointment_id is not None:
            if attrs.get("appointment_id") == previous_appointment_id:
                raise serializers.ValidationError(
                    "The current appointment ID cannot be the same as the previous appointment ID."
                )

            # Retrieve the specific appointment by ID
            previous_appointment = get_appointment_by_id(previous_appointment_id)
            if previous_appointment is None:
                raise serializers.ValidationError(
                    "Appointment with this ID does not exist."
                )

        return attrs


class ValidateScheduledAppointmentInput(serializers.Serializer):
    organization = serializers.IntegerField(required=True)
    category = serializers.IntegerField(required=True)
    user = serializers.IntegerField(required=True)
    scheduled_time = serializers.DateTimeField(required=True)

    def validate_organization(self, value):
        """Validate if the organization exists and is active using the service layer."""
        organization = check_organization_is_active(value)
        if not organization:
            raise serializers.ValidationError(
                "Organization does not exist or is not active."
            )
        return value

    def validate_category(self, value):
        """Validate if the category exists and is active using the service layer."""
        category = check_category_is_active(value)

        if not category:
            raise serializers.ValidationError(
                "Category does not exist or is not active."
            )
        
        if not category.is_scheduled:
            raise serializers.ValidationError(
                "Category does not accept appointments."
            )
        return value

    def validate_user(self, value):
        """Validate if the user exists and is allowed to create the appointment."""
        user = check_user_exists(value)
        if not user:
            raise serializers.ValidationError("User does not exist.")
        return value
    

    def validate(self, attrs):
        """Additional validations that depend on multiple fields."""
        request_user = self.context["request"].user  # The user making the request
        user_id = attrs.get("user")
        category_id = attrs.get("category")
        organization_id = attrs.get("organization")
        scheduled_time = attrs.get("scheduled_time")
        organization = check_organization_is_active(organization_id)
        category = check_category_is_active(category_id, organization)

        if not category:
           raise serializers.ValidationError("Category does not exist or is not accepting appointments.")
        
        category_timezone = category.time_zone

        # Convert scheduled_time to the category's time zone
        local_scheduled_time = convert_time_to_utc(scheduled_time, category_timezone)

        # Perform validation
        if local_scheduled_time < now():
            raise serializers.ValidationError("Scheduled time cannot be in the past.")
        
        # Perform validation: Check if scheduled_time is within the max advance days limit
        max_allowed_date = now() + timedelta(days=category.max_advance_days)
        if local_scheduled_time > max_allowed_date:
            raise serializers.ValidationError(
                f"Scheduled time cannot be more than {category.max_advance_days} days in advance."
            )

        authorized_category_ids = get_authorized_categories_for_user(
            request_user
        ).values_list("id", flat=True)
        is_user_authorized_for_category = category_id in authorized_category_ids

        if (
            request_user.id != user_id
            and not request_user.is_staff
            and not request_user.is_superuser
            and not is_user_authorized_for_category
        ):
            raise UnauthorizedAccessException(
                detail="Unauthorized to access this appointment."
            )
        
        validate_scheduled_appointment(category, scheduled_time)

        attrs["scheduled_end_time"] = scheduled_time + category.time_interval_per_appointment

        return attrs


class CreateAppointmentSerializer(serializers.ModelSerializer):
    # Define the format to exclude timezone information
    scheduled_time = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S')
    scheduled_end_time = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', required=False)

    class Meta:
        model = Appointment
        fields = ["user", "category", "organization", "scheduled_time", "scheduled_end_time"]


class SlotQueryParamsSerializer(serializers.Serializer):
    date = serializers.CharField(required=True)
    category_id = serializers.IntegerField(required=True)

    def validate_date(self, value):
        """Validate and convert date string to a date object."""
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise serializers.ValidationError("Invalid date format. Use 'YYYY-MM-DD'.")
    
    def validate_category_id(self, value):
        """Validate if the category exists and is active using the service layer."""
        category = check_category_is_active(value)

        if not category:
            raise serializers.ValidationError(
                "Category does not exist or is not active."
            )
        
        if not category.is_scheduled:
            raise serializers.ValidationError(
                "Category does not accept appointments."
            )
        return value

    def validate(self, attrs):
        """Perform cross-field validation if needed."""
        return attrs