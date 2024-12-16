import pytest
from main.models import Category, User, Organization
from rest_framework.test import APIRequestFactory
from datetime import datetime, timedelta
from pytz import UTC
from main.appointments.serializers import SlotQueryParamsSerializer, ValidateScheduledAppointmentInput
from main.models import Category, Organization, User

# Mocks
from unittest.mock import patch, Mock


@pytest.mark.django_db
class TestValidateScheduledAppointmentInput:
    @patch("main.appointments.serializers.check_organization_is_active")
    @patch("main.appointments.serializers.check_category_is_active")
    @patch("main.appointments.serializers.check_user_exists")
    @patch("main.appointments.serializers.get_authorized_categories_for_user")
    @patch("main.appointments.serializers.validate_scheduled_appointment")
    @patch("main.appointments.serializers.convert_time_to_utc")
    @patch("main.appointments.serializers.now")
    def test_valid_input(
        self,
        mock_now,
        mock_convert_time_to_utc,
        mock_validate_scheduled_appointment,
        mock_get_authorized_categories_for_user,
        mock_check_user_exists,
        mock_check_category_is_active,
        mock_check_organization_is_active,
    ):
        # Setup
        mock_now.return_value = datetime(2024, 11, 15, 12, 0, tzinfo=UTC)
        mock_convert_time_to_utc.return_value = datetime(2024, 11, 16, 12, 0, tzinfo=UTC)
        mock_check_organization_is_active.return_value = True
        mock_check_category_is_active.return_value = Mock(
            is_scheduled=True, max_advance_days=7, time_zone="UTC", time_interval_per_appointment=timedelta(minutes=30)
        )
        mock_check_user_exists.return_value = True
        mock_get_authorized_categories_for_user.return_value = Mock(values_list=Mock(return_value=[1]))

        factory = APIRequestFactory()
        request = factory.post("/appointments/schedule/")
        request.user = Mock(id=1, is_staff=False, is_superuser=False)

        serializer = ValidateScheduledAppointmentInput(
            data={
                "organization": 1,
                "category": 1,
                "user": 1,
                "scheduled_time": "2024-11-16T12:00:00Z",
            },
            context={"request": request},
        )

        # Test
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["scheduled_end_time"] == datetime(2024, 11, 16, 12, 30, tzinfo=UTC)

    def test_missing_fields(self):
        serializer = ValidateScheduledAppointmentInput(data={})
        assert not serializer.is_valid()
        assert set(serializer.errors.keys()) == {"organization", "category", "user", "scheduled_time"}

    @patch("main.appointments.serializers.check_organization_is_active")
    def test_invalid_organization(self, mock_check_organization_is_active):
        mock_check_organization_is_active.return_value = None

        serializer = ValidateScheduledAppointmentInput(data={"organization": 1, "category": 1, "user": 1, "scheduled_time": "2024-11-16T12:00:00Z"})
        assert not serializer.is_valid()
        assert "Organization does not exist or is not active." in serializer.errors["organization"]

    @patch("main.appointments.serializers.check_category_is_active")
    def test_inactive_category(self, mock_check_category_is_active):
        mock_check_category_is_active.return_value = None

        serializer = ValidateScheduledAppointmentInput(data={"organization": 1, "category": 1, "user": 1, "scheduled_time": "2024-11-16T12:00:00Z"})
        assert not serializer.is_valid()
        assert "Category does not exist or is not active." in serializer.errors["category"]

    @patch("main.appointments.serializers.check_user_exists")
    def test_invalid_user(self, mock_check_user_exists):
        mock_check_user_exists.return_value = None

        serializer = ValidateScheduledAppointmentInput(data={"organization": 1, "category": 1, "user": 1, "scheduled_time": "2024-11-16T12:00:00Z"})
        assert not serializer.is_valid()
        assert "User does not exist." in serializer.errors["user"]

    @patch("main.appointments.serializers.now")
    @patch("main.appointments.serializers.check_category_is_active")
    def test_scheduled_time_in_past(self, mock_check_category_is_active, mock_now, mocker):
        mock_now.return_value = datetime(2024, 11, 15, 12, 0, tzinfo=UTC)
        mock_check_category_is_active.return_value = Mock(is_scheduled=True, max_advance_days=7, time_zone="UTC")

        mocker.patch("main.appointments.serializers.check_organization_is_active", return_value=True)
        mocker.patch("main.appointments.serializers.check_user_exists", return_value=True)
        factory = APIRequestFactory()
        request = factory.post("/appointments/schedule/")
        request.user = Mock(id=1, is_staff=False, is_superuser=False)

        serializer = ValidateScheduledAppointmentInput(
            data={"organization": 1, "category": 1, "user": 1, "scheduled_time": "2024-11-14T12:00:00Z"},
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "Scheduled time cannot be in the past." in serializer.errors["non_field_errors"]

    @patch("main.appointments.serializers.now")
    @patch("main.appointments.serializers.check_category_is_active")
    def test_scheduled_time_exceeds_max_days(self, mock_check_category_is_active, mock_now, mocker):
        mock_now.return_value = datetime(2024, 11, 15, 12, 0, tzinfo=UTC)
        mock_check_category_is_active.return_value = Mock(is_scheduled=True, max_advance_days=7, time_zone="UTC")

        mocker.patch("main.appointments.serializers.check_organization_is_active", return_value=True)
        mocker.patch("main.appointments.serializers.check_user_exists", return_value=True)
        factory = APIRequestFactory()
        request = factory.post("/appointments/schedule/")
        request.user = Mock(id=1, is_staff=False, is_superuser=False)

        serializer = ValidateScheduledAppointmentInput(
            data={"organization": 1, "category": 1, "user": 1, "scheduled_time": "2024-11-25T12:00:00Z"},
            context={"request": request}
        )
        assert not serializer.is_valid()
        assert "Scheduled time cannot be more than 7 days in advance." in serializer.errors["non_field_errors"]


@pytest.mark.django_db
class TestSlotQueryParamsSerializer:
    """Test suite for the `SlotQueryParamsSerializer`."""

    def setup_method(self):
        """Set up common test data for category and user."""
        self.created_by = User.objects.create_user(username="testuser", password="password")
        self.organization = Organization.objects.create(name="Test Organization", created_by=self.created_by)

        # Create an active category that accepts appointments
        self.category = Category.objects.create(
            name="Test Category",
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True,
            time_interval_per_appointment=timedelta(minutes=15),
            time_zone="America/New_York",
            status="active",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={},
        )
        self.category.save()

    def test_valid_date_and_category(self):
        """Test valid date and category ID."""
        valid_data = {
            "date": "2024-11-25",  # Valid date format
            "category_id": self.category.id,  # Valid category ID
        }

        serializer = SlotQueryParamsSerializer(data=valid_data)
        assert serializer.is_valid()  # Should pass validation
        assert serializer.validated_data["date"] == datetime.strptime("2024-11-25", "%Y-%m-%d").date()
        assert serializer.validated_data["category_id"] == self.category.id

    def test_invalid_date_format(self):
        """Test invalid date format."""
        invalid_data = {
            "date": "2024-11-32",  # Invalid date (no 32nd day)
            "category_id": self.category.id,
        }

        serializer = SlotQueryParamsSerializer(data=invalid_data)
        assert not serializer.is_valid()  # Should not pass validation
        assert "date" in serializer.errors
        assert serializer.errors["date"] == ["Invalid date format. Use 'YYYY-MM-DD'."]

    def test_missing_date(self):
        """Test missing date field."""
        invalid_data = {
            "category_id": self.category.id,
        }

        serializer = SlotQueryParamsSerializer(data=invalid_data)
        assert not serializer.is_valid()  # Should not pass validation
        assert "date" in serializer.errors
        assert serializer.errors["date"] == ["This field is required."]

    def test_invalid_category_id(self):
        """Test invalid category ID (non-existent category)."""
        invalid_data = {
            "date": "2024-11-25",
            "category_id": 99999,  # Invalid category ID
        }

        serializer = SlotQueryParamsSerializer(data=invalid_data)
        assert not serializer.is_valid()  # Should not pass validation
        assert "category_id" in serializer.errors
        assert serializer.errors["category_id"] == ["Category does not exist or is not active."]

    def test_inactive_category(self):
        """Test inactive category ID."""
        # Create an inactive category
        inactive_category = Category.objects.create(
            name="Inactive Category",
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=False,  # This category does not accept appointments
            time_interval_per_appointment=timedelta(minutes=15),
            time_zone="America/New_York",
            status="inactive",
            opening_hours={"Monday": [["09:00", "17:00"]]},
            break_hours={},
        )
        inactive_category.save()

        invalid_data = {
            "date": "2024-11-25",
            "category_id": inactive_category.id,  # Invalid category ID (inactive category)
        }

        serializer = SlotQueryParamsSerializer(data=invalid_data)
        assert not serializer.is_valid()  # Should not pass validation
        assert "category_id" in serializer.errors
        assert serializer.errors["category_id"] == ["Category does not exist or is not active."]

    def test_category_not_accepting_appointments(self):
        """Test category that does not accept appointments."""
        # Create a category that does not accept appointments
        inactive_category = Category.objects.create(
            name="Not Accepting Appointments",
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=False,  # This category does not accept appointments
            time_interval_per_appointment=timedelta(minutes=15),
            time_zone="America/New_York",
            status="active",
            opening_hours={"Monday": [["09:00", "17:00"]]},
            break_hours={},
        )
        inactive_category.save()

        invalid_data = {
            "date": "2024-11-25",
            "category_id": inactive_category.id,  # Invalid category ID (does not accept appointments)
        }

        serializer = SlotQueryParamsSerializer(data=invalid_data)
        assert not serializer.is_valid()  # Should not pass validation
        assert "category_id" in serializer.errors
        assert serializer.errors["category_id"] == ["Category does not accept appointments."]
