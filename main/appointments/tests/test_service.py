import pytest
from main.models import Appointment, Category, Organization
from main.appointments.service import handle_appointment_scheduling, move_appointment
from django.contrib.auth.models import User

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
