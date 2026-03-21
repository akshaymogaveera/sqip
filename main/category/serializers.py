from rest_framework import serializers
from main.models import Category
from main.service import get_category, get_authorized_categories_for_user
from main.exceptions import UnauthorizedAccessException
from datetime import timedelta


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"  # Or list specific fields if needed

    def to_internal_value(self, data):
        """Accept time_interval_per_appointment as integer minutes or HH:MM:SS string."""
        data = super().to_internal_value(data)
        return data

    def validate_time_interval_per_appointment(self, value):
        """
        Accept an integer (minutes) or a timedelta.
        Converts plain integers so the frontend can send e.g. 15 meaning '15 minutes'
        without Django silently treating it as 15 seconds.
        """
        if isinstance(value, int):
            if value <= 0:
                raise serializers.ValidationError("Interval must be a positive number of minutes.")
            return timedelta(minutes=value)
        if isinstance(value, timedelta):
            if value.total_seconds() <= 0:
                raise serializers.ValidationError("Interval must be a positive duration.")
            return value
        # DRF has already parsed a duration string into a timedelta by this point,
        # so anything else falling through here is already correct.
        return value

    def to_representation(self, instance):
        """Return time_interval_per_appointment as integer minutes for easy frontend consumption."""
        data = super().to_representation(instance)
        interval = instance.time_interval_per_appointment
        if interval is not None:
            try:
                total_seconds = interval.total_seconds()
                mins = int(total_seconds // 60)
                data['time_interval_per_appointment'] = mins
            except Exception:
                pass
        return data


class ValidateCategorySerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Category.STATUS_CHOICES)

    def validate(self, attrs):
        """Additional validations that depend on multiple fields."""

        category_id = attrs.get("category_id")
        status = attrs.get("status")
        request = self.context.get("request")
        user = request.user

        category = get_category(category_id)
        # Validate category ID using the service method
        if not category:
            raise serializers.ValidationError("Invalid category ID.")

        if status and status not in dict(Category.STATUS_CHOICES).keys():
            raise serializers.ValidationError(f"Invalid status: {status}")

        # if user is admin.
        if user.is_staff or user.is_superuser:
            return attrs

        # Retrieve authorized categories for the user
        authorized_categories = get_authorized_categories_for_user(user)
        # Check if the appointment's category is within the authorized categories
        if category not in authorized_categories:
            raise UnauthorizedAccessException(
                detail="Unauthorized to access this category."
            )

        return attrs
