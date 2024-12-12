from datetime import datetime, timedelta
import pytest
import pytz
from main.models import Appointment, Category, Organization
from main.appointments.service import (
    handle_appointment_scheduling,
    is_within_opening_hours,
    move_appointment,
    activate_appointment,
    validate_scheduled_appointment,
    validate_time_alignment,
)
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from main.service import adjust_appointment_counter


@pytest.mark.django_db
class TestHandleAppointmentScheduling:

    def setup_method(self):
        """Set up data for testing."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        # Create active and inactive organizations
        self.organization_active = Organization.objects.create(
            name="Active Organization", created_by=self.user, status="active"
        )
        self.organization_inactive = Organization.objects.create(
            name="Inactive Organization", created_by=self.user, status="inactive"
        )

        # Create active and inactive categories
        self.category_active = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )
        self.category_inactive = Category.objects.create(
            organization=self.organization_active,
            status="inactive",
            created_by=self.user,
        )

        # Create an existing appointment
        Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            is_scheduled=False,
        )

    def test_valid_appointment_scheduling(self):
        """Test valid appointment scheduling returns a counter."""
        user_new = User.objects.create_user(
            username="testuser1", password="testpassword"
        )
        input_data = {
            "organization": self.organization_active.id,
            "category": self.category_active.id,
            "user": user_new.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter == 2  # Expect a valid counter
        assert msg is None  # No error message

    def test_inactive_organization(self):
        """Test handling scheduling with an inactive organization."""
        input_data = {
            "organization": self.organization_inactive.id,
            "category": self.category_active.id,
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Organization does not exist or is not accepting appointments."

    def test_inactive_category(self):
        """Test handling scheduling with an inactive category."""
        input_data = {
            "organization": self.organization_active.id,
            "category": self.category_inactive.id,
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."

    def test_duplicate_appointment(self):
        """Test handling scheduling with a duplicate appointment."""
        input_data = {
            "organization": self.organization_active.id,
            "category": self.category_active.id,
            "user": self.user.id,
        }
        # Create a duplicate appointment
        Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            is_scheduled=False,
        )

        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter due to duplicate
        assert msg == "Appointment already exists."

    def test_organization_not_found(self):
        """Test scheduling with a non-existing organization ID."""
        input_data = {
            "organization": 9999,  # Non-existing organization
            "category": self.category_active.id,
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Organization does not exist or is not accepting appointments."

    def test_category_not_found(self):
        """Test scheduling with a non-existing category ID."""
        input_data = {
            "organization": self.organization_active.id,
            "category": 9999,  # Non-existing category
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."

    def test_scheduling_for_different_user(self):
        """Test scheduling for a different user with a valid appointment."""
        another_user = User.objects.create_user(
            username="anotheruser", password="anotherpassword"
        )
        input_data = {
            "organization": self.organization_active.id,
            "category": self.category_active.id,
            "user": another_user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is not None  # Expect a valid counter
        assert msg is None  # No error message

    def test_multiple_active_categories(self):
        """Test scheduling with multiple active categories for the same organization."""
        another_category = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )

        input_data = {
            "organization": self.organization_active.id,
            "category": another_category.id,
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is not None  # Expect a valid counter
        assert msg is None  # No error message

    def test_active_organization_no_categories(self):
        """Test handling scheduling when the organization is active but has no categories."""
        empty_organization = Organization.objects.create(
            name="Empty Organization", created_by=self.user, status="active"
        )
        input_data = {
            "organization": empty_organization.id,
            "category": self.category_active.id,
            "user": self.user.id,
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."


@pytest.mark.django_db
class TestAdjustAppointmentCounter:
    """
    Test class for appointment counter adjustments and position changes.
    """

    @pytest.fixture
    def setup_appointments(self):
        """
        Fixture to set up a list of 10 appointments with sequential counters for testing purposes.

        Creates:
            - User: Test user for creating and associating appointments.
            - Organization: Organization object for appointments.
            - Category: Category associated with the organization.
            - Appointments: 10 appointments with counters from 1 to 10.
        """
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        organization = Organization.objects.create(
            name="Active Organization", created_by=self.user, status="active"
        )

        category = Category.objects.create(
            organization=organization, status="active", created_by=self.user
        )

        # Create 10 sequential appointments for testing
        appointments = [
            Appointment.objects.create(
                organization=organization,
                category=category,
                status="active",
                counter=i,
                is_scheduled=False,
                user=self.user,
            )
            for i in range(1, 11)
        ]
        return appointments

    def test_increment_counters(self, setup_appointments):
        """
        Test that counters are incremented correctly for appointments with counters above the reference.
        """
        appointment_to_adjust = setup_appointments[2]  # Example counter = 3
        reference_counter = appointment_to_adjust.counter

        # Initial counters to verify changes
        initial_counters = {app.id: app.counter for app in setup_appointments}

        adjust_appointment_counter(
            appointment_to_adjust, increment=True, reference_counter=reference_counter
        )

        # Verify that only counters > 3 were incremented
        for app in Appointment.objects.all():
            if initial_counters[app.id] > reference_counter:
                assert app.counter == initial_counters[app.id] + 1
            else:
                assert app.counter == initial_counters[app.id]

    def test_decrement_counters(self, setup_appointments):
        """
        Test that counters are decremented correctly for appointments with counters above the reference.
        """
        reference_counter = 3
        appointment = setup_appointments[0]
        initial_counters = {app.id: app.counter for app in setup_appointments}

        adjust_appointment_counter(
            appointment, increment=False, reference_counter=reference_counter
        )

        # Verify that only counters > 3 were decremented
        for app in Appointment.objects.all():
            if initial_counters[app.id] > reference_counter:
                assert app.counter == initial_counters[app.id] - 1
            else:
                assert app.counter == initial_counters[app.id]

    def test_no_counter_adjustment_for_other_statuses(self, setup_appointments):
        """
        Test that inactive appointments do not have their counters adjusted.
        """
        reference_counter = 2
        appointment = setup_appointments[0]

        # Create inactive appointment
        inactive_appointment = Appointment.objects.create(
            organization_id=appointment.organization.id,
            category_id=appointment.category.id,
            status="inactive",
            counter=4,
            is_scheduled=False,
            user=self.user,
        )

        adjust_appointment_counter(
            appointment, increment=True, reference_counter=reference_counter
        )

        # Ensure inactive appointment counter remains unchanged
        inactive_appointment.refresh_from_db()
        assert inactive_appointment.counter == 4

    def test_counter_adjustment_does_not_affect_scheduled_appointments(
        self, setup_appointments
    ):
        """
        Test that scheduled appointments do not have their counters adjusted.
        """
        reference_counter = 2
        appointment = setup_appointments[0]

        # Create scheduled appointment
        scheduled_appointment = Appointment.objects.create(
            organization_id=appointment.organization.id,
            category_id=appointment.category.id,
            status="active",
            counter=5,
            is_scheduled=True,
            user=self.user,
        )

        adjust_appointment_counter(
            appointment, increment=True, reference_counter=reference_counter
        )

        # Ensure scheduled appointment counter remains unchanged
        scheduled_appointment.refresh_from_db()
        assert scheduled_appointment.counter == 5

    def test_increment_counters_with_counter_limit(self, setup_appointments):
        """
        Test that counters are incremented correctly for appointments within the specified counter range.
        """
        appointment_to_adjust = setup_appointments[2]  # Example counter = 3
        reference_counter = appointment_to_adjust.counter
        counter_limit = 8

        # Initial counters to verify changes
        initial_counters = {app.id: app.counter for app in setup_appointments}

        adjust_appointment_counter(
            appointment_to_adjust,
            increment=True,
            reference_counter=reference_counter,
            counter_limit=counter_limit,
        )

        # Verify that only counters > 3 and < 8 were incremented
        for app in Appointment.objects.all():
            if reference_counter < initial_counters[app.id] < counter_limit:
                assert app.counter == initial_counters[app.id] + 1
            else:
                assert app.counter == initial_counters[app.id]

    def test_decrement_counters_with_counter_limit(self, setup_appointments):
        """
        Test that counters are decremented correctly for appointments within the specified counter range.
        """
        appointment_to_adjust = setup_appointments[0]
        reference_counter = 3
        counter_limit = 7

        # Initial counters to verify changes
        initial_counters = {app.id: app.counter for app in setup_appointments}

        adjust_appointment_counter(
            appointment_to_adjust,
            increment=False,
            reference_counter=reference_counter,
            counter_limit=counter_limit,
        )

        # Verify that only counters > 3 and < 7 were decremented
        for app in Appointment.objects.all():
            if reference_counter < initial_counters[app.id] < counter_limit:
                assert app.counter == initial_counters[app.id] - 1
            else:
                assert app.counter == initial_counters[app.id]

    def test_no_appointments_updated_outside_counter_limit(self, setup_appointments):
        """
        Test that no appointments are updated when counter_limit excludes all counters.
        """
        appointment_to_adjust = setup_appointments[2]  # Example counter = 3
        reference_counter = appointment_to_adjust.counter
        counter_limit = 4  # Only counter = 3 is eligible, but it's excluded by counter_limit

        # Initial counters to verify no changes
        initial_counters = {app.id: app.counter for app in setup_appointments}

        adjust_appointment_counter(
            appointment_to_adjust,
            increment=True,
            reference_counter=reference_counter,
            counter_limit=counter_limit,
        )

        # Verify that no counters were changed
        for app in Appointment.objects.all():
            assert app.counter == initial_counters[app.id]

    def test_counter_limit_with_scheduled_appointments(self, setup_appointments):
        """
        Test that scheduled appointments are not affected even if they fall within the counter range.
        """
        appointment_to_adjust = setup_appointments[0]
        reference_counter = 2
        counter_limit = 7

        # Create a scheduled appointment within the counter range
        scheduled_appointment = Appointment.objects.create(
            organization_id=appointment_to_adjust.organization.id,
            category_id=appointment_to_adjust.category.id,
            status="active",
            counter=5,
            is_scheduled=True,
            user=self.user,
        )

        initial_counters = {app.id: app.counter for app in setup_appointments}
        initial_scheduled_counter = scheduled_appointment.counter

        adjust_appointment_counter(
            appointment_to_adjust,
            increment=False,
            reference_counter=reference_counter,
            counter_limit=counter_limit,
        )

        # Verify scheduled appointment is unaffected
        scheduled_appointment.refresh_from_db()
        assert scheduled_appointment.counter == initial_scheduled_counter

        # Verify other appointments in the range are updated
        for app in Appointment.objects.exclude(id=scheduled_appointment.id):
            if reference_counter < initial_counters[app.id] < counter_limit:
                assert app.counter == initial_counters[app.id] - 1
            else:
                assert app.counter == initial_counters[app.id]


    def test_move_middle_to_first_position(self, setup_appointments):
        """
        Test moving an appointment to the first position.
        """
        appointment_to_move = setup_appointments[4]
        move_appointment(
            current_appointment_id=appointment_to_move.id, previous_appointment_id=None
        )

        # Validate new position and order
        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == 1
        self._validate_unique_and_ordered_counters()

    def test_move_from_last_to_first(self, setup_appointments):
        """
        Test moving the last appointment to the first position.
        """
        last_appointment = setup_appointments[-1]
        move_appointment(
            current_appointment_id=last_appointment.id, previous_appointment_id=None
        )

        last_appointment.refresh_from_db()
        assert last_appointment.counter == 1
        self._validate_unique_and_ordered_counters()

    def test_move_to_last_position(self, setup_appointments):
        """
        Test moving an appointment to the last position.
        """
        appointment_to_move = setup_appointments[1]
        last_appointment_id = setup_appointments[-1].id
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=last_appointment_id,
        )

        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == 10
        self._validate_unique_and_ordered_counters()

    def test_move_middle_to_last_position(self, setup_appointments):
        """
        Test moving an appointment to the last position.
        """
        appointment_to_move = setup_appointments[5]
        last_appointment_id = setup_appointments[-1].id
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=last_appointment_id,
        )

        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == 10
        self._validate_unique_and_ordered_counters()

    def test_move_within_middle(self, setup_appointments):
        """
        Test moving an appointment within the middle positions.
        """
        appointment_to_move = setup_appointments[2]
        target_appointment = setup_appointments[6]
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=target_appointment.id,
        )
        target_appointment.refresh_from_db()
        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == target_appointment.counter + 1
        self._validate_unique_and_ordered_counters()

    def test_move_within_middle_2(self, setup_appointments):
        # Case 2: Move appointment from counter 7 to follow counter 3
        appointment_to_move = setup_appointments[6]
        target_appointment = setup_appointments[2]
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=target_appointment.id,
        )

        target_appointment.refresh_from_db()
        appointment_to_move.refresh_from_db()
        assert (
            appointment_to_move.counter == target_appointment.counter + 1
        )  # New position after target
        self._validate_unique_and_ordered_counters()

    def test_move_to_same_position(self, setup_appointments):
        """
        Test moving an appointment to its own position.
        """
        appointment_to_move = setup_appointments[3]
        current_counter = appointment_to_move.counter
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=current_counter - 1,
        )

        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == current_counter
        self._validate_unique_and_ordered_counters()

    def test_move_non_adjacent(self, setup_appointments):
        """
        Test moving an appointment from one end to a non-adjacent position.
        """
        appointment_to_move = setup_appointments[9]
        target_appointment = setup_appointments[4]
        move_appointment(
            current_appointment_id=appointment_to_move.id,
            previous_appointment_id=target_appointment.id,
        )

        appointment_to_move.refresh_from_db()
        assert appointment_to_move.counter == target_appointment.counter + 1
        self._validate_unique_and_ordered_counters()

    def _validate_unique_and_ordered_counters(self):
        """
        Helper function to validate that appointment counters are unique and sequential from 1 to the total number of appointments.
        """
        updated_appointments = Appointment.objects.order_by("counter")
        counters = [app.counter for app in updated_appointments]

        # Ensure sequential unique counters from 1 to len(updated_appointments)
        expected_counters = list(range(1, len(updated_appointments) + 1))
        assert (
            counters == expected_counters
        ), f"Expected counters: {expected_counters}, but got: {counters}"


@pytest.mark.django_db
class TestActivateAppointment:
    """
    Test class for the `activate_appointment` function.
    """

    @pytest.fixture
    def setup_appointments(self):
        """
        Fixture to set up appointments for testing.

        Creates:
            - User: Test user for creating appointments.
            - Organization: Active organization for appointments.
            - Category: Active category for appointments.
            - Appointments: 
                - Active scheduled appointment
                - Inactive unscheduled appointment
                - Already active appointment
        """
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        organization = Organization.objects.create(
            name="Test Organization", created_by=self.user, status="active"
        )

        category = Category.objects.create(
            organization=organization, status="active", created_by=self.user
        )

        appointments = {
            "active_scheduled": Appointment.objects.create(
                organization=organization,
                category=category,
                status="active",
                counter=1,
                is_scheduled=True,
                user=self.user,
            ),
            "inactive_unscheduled": Appointment.objects.create(
                organization=organization,
                category=category,
                status="inactive",
                counter=2,
                is_scheduled=False,
                user=self.user,
            ),
            "already_active": Appointment.objects.create(
                organization=organization,
                category=category,
                status="active",
                counter=3,
                is_scheduled=False,
                user=self.user,
            ),
        }
        return appointments

    def test_activate_unscheduled_inactive_appointment(self, setup_appointments, mocker):
        """
        Test that an inactive and unscheduled appointment is activated successfully.
        """
        appointment = setup_appointments["inactive_unscheduled"]

        # Mock handle_appointment_scheduling to avoid external dependencies
        mock_handle_scheduling = mocker.patch(
            "main.appointments.service.handle_appointment_scheduling",
            return_value=(10, None),
        )

        success, result = activate_appointment(appointment.id)

        appointment.refresh_from_db()

        assert success is True
        assert result["status"] == "active"
        assert result["counter"] == 10
        assert appointment.status == "active"
        assert appointment.counter == 10

    def test_activate_already_active_appointment(self, setup_appointments):
        """
        Test that an already active appointment cannot be activated again.
        """
        appointment = setup_appointments["already_active"]

        success, result = activate_appointment(appointment.id)

        assert success is False
        assert result == "Invalid Appointment: Already active or scheduled."

    def test_activate_scheduled_appointment(self, setup_appointments):
        """
        Test that a scheduled appointment cannot be activated.
        """
        appointment = setup_appointments["active_scheduled"]

        success, result = activate_appointment(appointment.id)

        assert success is False
        assert result == "Invalid Appointment: Already active or scheduled."

    def test_handle_scheduling_error(self, setup_appointments, mocker):
        """
        Test that activation fails if scheduling logic returns an error.
        """
        appointment = setup_appointments["inactive_unscheduled"]

        # Mock handle_appointment_scheduling to simulate an error
        mock_handle_scheduling = mocker.patch(
            "main.appointments.service.handle_appointment_scheduling",
            return_value=(None, "Some scheduling error"),
        )

        success, result = activate_appointment(appointment.id)

        assert success is False
        assert result == "Scheduling Error: Some scheduling error"

        # Ensure the appointment was not updated
        appointment.refresh_from_db()
        assert appointment.status == "inactive"
        assert appointment.counter == 2

        # Ensure scheduling logic was called
        mock_handle_scheduling.assert_called_once_with(appointment.as_dict())


class TestIsWithinOpeningHours:
    """Test suite for the `is_within_opening_hours` function."""

    def setup_method(self):
        """Setup common test variables."""
        self.category_timezone = "America/New_York"  # Example timezone
        self.tz = pytz.timezone(self.category_timezone)  # Get the timezone object

    def test_within_opening_hours(self):
        """Test case where scheduled time is within valid opening hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 28, 10, 0)  # 10:00 AM
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid during opening hours."

    def test_outside_opening_hours(self):
        """Test case where scheduled time is outside valid opening hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 18, 0))  # 6:00 PM (after hours)
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid outside opening hours."

    def test_during_break_hours(self):
        """Test case where scheduled time falls within break hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 28, 12, 30)  # 12:30 PM (break time)
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid during break hours."

    def test_edge_case_start_of_opening_hours(self):
        """Test case where scheduled time is exactly at the start of opening hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 9, 0))  # 9:00 AM (start time)
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid at the start of opening hours."

    def test_edge_case_end_of_opening_hours(self):
        """Test case where scheduled time is exactly at the end of opening hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 17, 0))  # 5:00 PM (end time)
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid at the end of opening hours."

    def test_empty_opening_hours(self):
        """Test case where opening hours are empty."""
        opening_hours = []
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 10, 0))  # 10:00 AM
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid when opening hours are empty."

    def test_empty_break_hours(self):
        """Test case where break hours are empty."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = []
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 12, 30))  # 12:30 PM
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid when break hours are empty."

    def test_timezone_naive_scheduled_time(self):
        """Test case where the scheduled time is naive (no timezone information)."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 28, 10, 0)  # Naive datetime
        
        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Function should correctly handle naive scheduled time."

    def test_invalid_timezone(self):
        """Test case with an invalid timezone string."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 10, 0))  # 10:00 AM

        with pytest.raises(pytz.UnknownTimeZoneError):
            is_within_opening_hours(scheduled_time, opening_hours, break_hours, "Invalid/Timezone")


    def test_multiple_opening_ranges(self):
        """Test case where multiple opening ranges exist."""
        opening_hours = [["09:00", "12:00"], ["13:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 14, 0))  # 2:00 PM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid within any of the opening ranges."

    def test_outside_all_opening_ranges(self):
        """Test case where scheduled time is outside all opening ranges."""
        opening_hours = [["09:00", "12:00"], ["13:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 18, 0))  # 6:00 PM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid outside all opening ranges."

    def test_multiple_break_ranges(self):
        """Test case where multiple break ranges exist."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["10:30", "11:00"], ["14:00", "14:30"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 14, 15))  # 2:15 PM (during break)

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid during any of the break ranges."

    def test_edge_case_end_of_break_hours(self):
        """Test case where scheduled time is exactly at the end of break hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 13, 0))  # 1:00 PM (end of break)

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid exactly at the end of break hours."

    def test_spanning_opening_hours(self):
        """Test case where opening hours span past midnight."""
        opening_hours = [["22:00", "02:00"]]  # 10:00 PM to 2:00 AM
        break_hours = [["23:30", "00:30"]]  # Break from 11:30 PM to 12:30 AM
        scheduled_time = self.tz.localize(datetime(2024, 11, 29, 0, 15))  # 12:15 AM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid during a spanning break range."

    def test_exactly_on_midnight(self):
        """Test case where scheduled time is exactly at midnight."""
        opening_hours = [["00:00", "02:00"]]  # Midnight to 2:00 AM
        break_hours = []
        scheduled_time = self.tz.localize(datetime(2024, 11, 29, 0, 0))  # 12:00 AM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid exactly at midnight within opening hours."

    def test_timezone_conversion(self):
        """Test case for scheduled time in a different timezone."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = pytz.timezone("UTC").localize(datetime(2024, 11, 28, 14, 0))  # 2:00 PM UTC

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Function should correctly handle timezones and validate the scheduled time."

    def test_large_opening_hours_range(self):
        """Test case where opening hours cover an entire day."""
        opening_hours = [["00:00", "23:59"]]  # Open all day
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 16, 0))  # 4:00 PM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is True, "Scheduled time should be valid for large opening ranges outside break hours."

    def test_empty_opening_and_break_hours(self):
        """Test case where both opening and break hours are empty."""
        opening_hours = []
        break_hours = []
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 10, 0))  # 10:00 AM

        result = is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)
        assert result is False, "Scheduled time should be invalid when both opening and break hours are empty."

    def test_naive_datetime_error(self):
        """Test case where scheduled time is naive and should fail."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 28, 10, 0)  # Naive datetime

        assert is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)

    def test_invalid_time_range_format(self):
        """Test case with an invalid time range format."""
        opening_hours = [["09:00"]]  # Invalid format (only start time provided)
        break_hours = [["12:00", "13:00"]]
        scheduled_time = self.tz.localize(datetime(2024, 11, 28, 10, 0))  # 10:00 AM

        with pytest.raises(IndexError):
            is_within_opening_hours(scheduled_time, opening_hours, break_hours, self.category_timezone)

class TestValidateTimeAlignment:
    """Test suite for the updated `validate_time_alignment` function."""

    def test_valid_time_matches_generated_slots(self, mocker):
        """Test that valid times matching the generated slots pass validation."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"], ["13:00", "13:15"]
        ])
        scheduled_time = datetime(2024, 11, 28, 9, 15)
        validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_invalid_time_does_not_match_generated_slots(self, mocker):
        """Test that times not matching the generated slots fail validation."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"], ["13:00", "13:15"]
        ])
        scheduled_time = datetime(2024, 11, 28, 9, 10)

        with pytest.raises(ValidationError, match="Scheduled time must match one of the available start times: 09:00, 09:15, 13:00"):
            validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_time_during_break_hours(self, mocker):
        """Test that a valid time during break hours fails validation."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"]
        ])
        scheduled_time = datetime(2024, 11, 28, 12, 0)

        with pytest.raises(ValidationError, match="Scheduled time must match one of the available start times"):
            validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_time_outside_opening_hours(self, mocker):
        """Test that a time outside opening hours fails validation."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"], ["13:00", "13:15"]
        ])
        scheduled_time = datetime(2024, 11, 28, 8, 45)

        with pytest.raises(ValidationError, match="Scheduled time must match one of the available start times"):
            validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_invalid_time_with_multiple_opening_ranges(self, mocker):
        """Test an invalid time with multiple opening hour ranges."""
        opening_hours = [["09:00", "12:00"], ["13:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"], ["13:00", "13:15"]
        ])
        scheduled_time = datetime(2024, 11, 28, 12, 15)

        with pytest.raises(ValidationError, match="Scheduled time must match one of the available start times"):
            validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_no_opening_hours(self, mocker):
        """Test when no opening hours are provided."""
        opening_hours = []
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[])
        scheduled_time = datetime(2024, 11, 28, 9, 0)

        with pytest.raises(ValidationError, match="Scheduled time must match one of the available start times"):
            validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_no_break_hours(self, mocker):
        """Test a valid time when no break hours are provided."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = []
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["09:15", "09:30"]
        ])
        scheduled_time = datetime(2024, 11, 28, 9, 15)
        validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)

    def test_slot_at_end_of_opening_hours(self, mocker):
        """Test a time slot at the end of the opening hours."""
        opening_hours = [["09:00", "17:00"]]
        break_hours = [["12:00", "13:00"]]
        mocker.patch("main.appointments.service.generate_time_slots", return_value=[
            ["09:00", "09:15"], ["16:45", "17:00"]
        ])
        scheduled_time = datetime(2024, 11, 28, 16, 45)
        validate_time_alignment(scheduled_time, 15, opening_hours, break_hours)


@pytest.mark.django_db
class TestValidateScheduledAppointment:
    """Test suite for the `validate_scheduled_appointment` function."""

    def setup_method(self):
        self.created_by = User.objects.create_user(username="testuser", password="password")
        self.organization = Organization.objects.create(name="Test Organization", created_by=self.created_by)
        """Set up common test data."""

        self.category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [],
                "Sunday": [["10:00", "14:00"]],  # Ensure non-empty range
            },
            break_hours={
            "Monday": [["12:00", "13:00"]],
            "Thursday": [["12:00", "13:00"]],
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True,
            time_interval_per_appointment = timedelta(minutes=15),
            time_zone = "America/New_York",
            status="active"
        )
        self.category.save()

    def test_valid_appointment(self, mocker):
        """Test a valid appointment within opening hours and not during break hours."""
        scheduled_time = datetime(2024, 11, 28, 9, 15)
        self.category.opening_hours["Thursday"] = [["09:00", "17:00"]]
        self.category.break_hours["Thursday"] = [["12:00", "13:00"]]

        with mocker.patch("main.appointments.service.is_slot_available", return_value=True):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_invalid_time_alignment(self):
        """Test appointment with invalid time alignment."""
        scheduled_time = datetime(2024, 11, 28, 9, 17)

        with pytest.raises(ValidationError):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_no_opening_hours_for_weekday(self):
        """Test appointment on a weekday with no opening hours defined."""
        scheduled_time = datetime(2024, 11, 30, 10, 0)  # Saturday

        with pytest.raises(ValidationError, match="Not accepting appointments for Saturday."):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_outside_opening_hours(self):
        """Test appointment outside opening hours."""
        scheduled_time = datetime(2024, 11, 28, 8, 45)  # Before 9:00 opening

        with pytest.raises(ValidationError, match="Scheduled time is not within allowed hours."):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_during_break_hours(self):
        """Test appointment during break hours."""
        scheduled_time = datetime(2024, 11, 28, 12, 30)  # During break

        with pytest.raises(ValidationError, match="Scheduled time is not within allowed hours."):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_slot_unavailable(self, mocker):
        """Test appointment when the time slot is already taken."""
        scheduled_time = datetime(2024, 11, 28, 9, 15)
        with mocker.patch("main.appointments.service.is_slot_available", return_value=False):
            with pytest.raises(ValidationError, match="The selected time slot is already taken."):
                validate_scheduled_appointment(self.category, scheduled_time)

    def test_valid_with_multiple_ranges(self, mocker):
        """Test valid appointment with multiple opening and break hour ranges."""
        self.category.opening_hours["Monday"] = [["09:00", "12:00"], ["13:00", "17:00"]]
        self.category.break_hours["Monday"] = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 25, 14, 0)  # Monday, within second range

        with mocker.patch("main.appointments.service.is_slot_available", return_value=True):
            with pytest.raises(ValidationError, match='Scheduled time must match one of the available start times: 09:00, 09:15, 09:30, 09:45, 10:00, 10:15, 10:30, 10:45, 11:00, 11:15, 11:30, 11:45.'):
                validate_scheduled_appointment(self.category, scheduled_time)

    def test_invalid_with_multiple_ranges(self):
        """Test invalid appointment with multiple opening and break hour ranges."""
        self.category.opening_hours["Monday"] = [["09:00", "12:00"], ["13:00", "17:00"]]
        self.category.break_hours["Monday"] = [["12:00", "13:00"]]
        scheduled_time = datetime(2024, 11, 25, 12, 30)  # During break

        with pytest.raises(ValidationError, match="Scheduled time is not within allowed hours."):
            validate_scheduled_appointment(self.category, scheduled_time)

    def test_time_zone_conversion(self, mocker):
        """Test validation with time zone differences."""
        self.category.time_zone = "US/Eastern"
        scheduled_time = datetime(2024, 11, 28, 9, 15)  # Valid in UTC
        self.category.opening_hours["Thursday"] = [["04:00", "12:00"]]  # Eastern time (UTC -5)

        with mocker.patch("main.appointments.service.is_slot_available", return_value=True):
            validate_scheduled_appointment(self.category, scheduled_time)
            