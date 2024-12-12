import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from datetime import datetime, timedelta
from pytz import UTC
from main.appointments.serializers import ValidateScheduledAppointmentInput
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
