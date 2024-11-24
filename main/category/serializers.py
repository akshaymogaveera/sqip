from rest_framework import serializers
from main.models import Category
from main.service import get_category, get_authorized_categories_for_user
from main.exceptions import UnauthorizedAccessException

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"  # Or list specific fields if needed


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
