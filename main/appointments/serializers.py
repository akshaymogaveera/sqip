from datetime import datetime, timedelta
import pytz
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
import phonenumbers
from main.models import Appointment, AppointmentNote, Category, Organization
from main.appointments.service import validate_scheduled_appointment
from main.utils import convert_time_to_utc


class AppointmentSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    category_description = serializers.SerializerMethodField()
    category_estimated_time = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    user_first_name = serializers.SerializerMethodField()
    user_last_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = "__all__"

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name or obj.category.description
        return None

    def get_category_description(self, obj):
        return obj.category.description if obj.category else None

    def get_category_estimated_time(self, obj):
        """Return category.estimated_time (minutes) so the frontend can compute wait time."""
        if obj.category and obj.category.estimated_time is not None:
            return obj.category.estimated_time
        return None

    def get_username(self, obj):
        return obj.user.username if obj.user else None

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_user_first_name(self, obj):
        try:
            return obj.user.first_name if obj.user and obj.user.first_name else None
        except Exception:
            return None

    def get_user_last_name(self, obj):
        try:
            return obj.user.last_name if obj.user and obj.user.last_name else None
        except Exception:
            return None

    def get_user_phone(self, obj):
        try:
            phone = obj.user.profile.phone_number
            # Ensure we return a JSON-serializable string (or None)
            if phone:
                return str(phone)
            return None
        except Exception:
            return None

    # Note: we intentionally do NOT include any category timezone or display-time
    # fields here. The client requests to avoid client-side timezone conversions
    # and avoid timezone labels; it will extract the HH:MM from the canonical
    # scheduled_time value. Keeping the serializer minimal prevents extra
    # timezone-tagged fields from being returned to the frontend.

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Remove keys with None or empty string values to keep responses concise
        for key in list(data.keys()):
            # Keep important fields even if null so clients can show placeholders
            if key in ("id", "status"):
                continue
            if data[key] is None or (isinstance(data[key], str) and data[key] == ""):
                data.pop(key, None)
        return data


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class ValidateAppointmentInput(serializers.Serializer):
    organization = serializers.IntegerField(required=True)
    category = serializers.IntegerField(required=True)
    user = serializers.IntegerField(required=True)


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

        # Be defensive: service may return a queryset-like object or a simple
        # iterable (or in tests a Mock). Try to call values_list() when
        # available, and coerce the result to a list for safe membership checks.
        _auth_cats = get_authorized_categories_for_user(request_user)
        # Normalize different return shapes (QuerySet-like, list, Mock).
        authorized_category_ids = []
        try:
            # Prefer values_list when present
            if hasattr(_auth_cats, "values_list"):
                ids_candidate = _auth_cats.values_list("id", flat=True)
            else:
                ids_candidate = _auth_cats

            # If the candidate is callable (e.g., a Mock), try calling it
            if callable(ids_candidate) and not hasattr(ids_candidate, "__iter__"):
                ids_candidate = ids_candidate()

            authorized_category_ids = list(ids_candidate)
        except Exception:
            authorized_category_ids = []

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

        # Defensive membership check as above (tests may patch the service
        # to return mocks that are not directly iterable).
        _auth_cats = get_authorized_categories_for_user(request_user)
        authorized_category_ids = []
        try:
            if hasattr(_auth_cats, "values_list"):
                ids_candidate = _auth_cats.values_list("id", flat=True)
            else:
                ids_candidate = _auth_cats
            if callable(ids_candidate) and not hasattr(ids_candidate, "__iter__"):
                ids_candidate = ids_candidate()
            authorized_category_ids = list(ids_candidate)
        except Exception:
            authorized_category_ids = []

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

        # Enforce per-user per-day scheduled appointment limit if configured on category.
        try:
            limit = getattr(category, 'max_scheduled_per_user_per_day', None)
        except Exception:
            limit = None

        # Only enforce for regular users (allow staff/superusers to bypass)
        request_user = self.context["request"].user
        # Coerce limit to an integer when possible. Tests may return Mock objects
        # for category attributes; safely treat non-int values as no-limit.
        try:
            if limit is not None:
                limit = int(limit)
        except Exception:
            limit = None

        if limit is not None and not (request_user.is_staff or request_user.is_superuser):
            # Determine the calendar day in the category timezone for the scheduled_time
            category_tz = pytz.timezone(category.time_zone)
            # Ensure naive localized datetime in category tz
            naive = scheduled_time
            if scheduled_time.tzinfo is not None:
                naive = scheduled_time.replace(tzinfo=None)
            local_dt = category_tz.localize(naive)
            day_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_start_utc = day_start.astimezone(pytz.utc)
            day_end_utc = day_end.astimezone(pytz.utc)

            # Count existing scheduled appointments for the target user on that day and category
            # Use the original category id from input attrs (an int) to avoid
            # passing Mock/category objects into ORM filters which may expose
            # Mock attributes that Django treats as expressions.
            existing_count = Appointment.objects.filter(
                user_id=attrs.get("user"),
                category_id=category_id,
                is_scheduled=True,
                status="active",
                scheduled_time__gte=day_start_utc,
                scheduled_time__lt=day_end_utc,
            ).count()

            if existing_count >= limit:
                raise serializers.ValidationError(
                    f"User already has {existing_count} scheduled appointment(s) on this date; the limit is {limit} per day."
                )

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


class AdminAddUserToQueueSerializer(serializers.Serializer):
    organization = serializers.IntegerField(required=True)
    category = serializers.IntegerField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    phone = serializers.CharField(required=True, max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_phone(self, value):
        # Expect an international number; normalize to E.164
        v = (value or '').strip()
        try:
            parsed = phonenumbers.parse(v, None)
        except Exception:
            raise serializers.ValidationError('Invalid phone number format')

        if not phonenumbers.is_valid_number(parsed):
            raise serializers.ValidationError('Phone number is not a valid international number')

        try:
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            raise serializers.ValidationError('Failed to normalize phone number')
        return e164

    def validate(self, attrs):
        # normalize phone into validated data
        phone = attrs.get('phone')
        attrs['phone'] = self.validate_phone(phone)
        return attrs


class AppointmentNoteSerializer(serializers.ModelSerializer):
    """Serializer for AppointmentNote.

    - All fields are read-only for regular users (enforced in the view).
    - `added_by_name` is a friendly display name derived from the User FK.
    - `has_file` is a convenience boolean so the client doesn't have to read
      the (potentially large) file_data field just to know a file exists.
    - `file_data` is excluded from list responses; only included when a
      single note is fetched (handled by the view) to avoid large payloads.
    """
    added_by_name = serializers.SerializerMethodField()
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentNote
        fields = [
            'id', 'appointment', 'content',
            'file_data', 'file_name', 'file_mime', 'has_file',
            'added_by', 'added_by_name', 'is_admin_note', 'created_at',
        ]
        read_only_fields = ['id', 'appointment', 'added_by', 'is_admin_note', 'created_at', 'added_by_name', 'has_file']

    def get_added_by_name(self, obj):
        if not obj.added_by:
            return None
        u = obj.added_by
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username

    def get_has_file(self, obj):
        return bool(obj.file_data)
