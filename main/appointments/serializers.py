# in your app/serializers.py

from main.service import check_category_is_active, check_organization_is_active, check_user_exists
from rest_framework import serializers
from main.models import Appointment, Category, Organization

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class ValidateAppointmentInput(serializers.Serializer):
    organization = serializers.IntegerField(required=True)
    category = serializers.IntegerField(required=True)
    user = serializers.IntegerField(required=True)
    is_scheduled = serializers.BooleanField(required=True)

    def validate_organization(self, value):
        """Validate if the organization exists and is active using the service layer."""
        organization = check_organization_is_active(value)
        if not organization:
            raise serializers.ValidationError("Organization does not exist or is not active.")
        return value

    def validate_category(self, value):
        """Validate if the category exists and is active using the service layer."""
        category = check_category_is_active(value)
        if not category:
            raise serializers.ValidationError("Category does not exist or is not active.")
        return value

    def validate_user(self, value):
        """Validate if the user exists and is allowed to create the appointment."""
        user = check_user_exists(value)
        if not user:
            raise serializers.ValidationError("User does not exist.")

        # Check if the user is trying to book an appointment for themselves
        request_user = self.context['request'].user  # The user making the request
        if request_user.id != value and not request_user.is_staff and not request_user.is_superuser:
            raise serializers.ValidationError("You are not allowed to create an appointment for this user.")

        return value

    def validate(self, data):
        """Additional validations that depend on multiple fields."""
        if not data.get('is_scheduled'):
            # Perform any additional validations for when is_scheduled is False
            pass
        return data


class MakeAppointmentSerializer(serializers.ModelSerializer):
    def validate(self, data):
        # Add custom validation for the serializer as a whole
        # For example, you can check if 'organization' is present and valid

        return data

    class Meta:
        model = Appointment
        fields = ['id', 'user', 'category', 'type', 'organization', 'status', 'date_created', 'counter', 'is_scheduled', 'estimated_time']
        