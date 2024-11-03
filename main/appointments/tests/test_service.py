import pytest
from main.models import Appointment, Category, Organization
from main.appointments.service import handle_appointment_scheduling
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestHandleAppointmentScheduling:

    def setup_method(self):
        """Set up data for testing."""
        # Create a user
        self.user = User.objects.create_user(username="testuser", password="testpassword")

        # Create active and inactive organizations
        self.organization_active = Organization.objects.create(
            name="Active Organization",
            created_by=self.user,
            status="active"
        )
        self.organization_inactive = Organization.objects.create(
            name="Inactive Organization",
            created_by=self.user,
            status="inactive"
        )

        # Create active and inactive categories
        self.category_active = Category.objects.create(
            organization=self.organization_active,
            status="active",
            created_by=self.user
        )
        self.category_inactive = Category.objects.create(
            organization=self.organization_active,
            status="inactive",
            created_by=self.user
        )

        # Create an existing appointment
        Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            is_scheduled=False
        )

    def test_valid_appointment_scheduling(self):
        """Test valid appointment scheduling returns a counter."""
        user_new = User.objects.create_user(username="testuser1", password="testpassword")
        input_data = {
            'organization': self.organization_active.id,
            'category': self.category_active.id,
            'user': user_new.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter == 2 # Expect a valid counter
        assert msg is None  # No error message

    def test_inactive_organization(self):
        """Test handling scheduling with an inactive organization."""
        input_data = {
            'organization': self.organization_inactive.id,
            'category': self.category_active.id,
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Organization does not exist or is not accepting appointments."

    def test_inactive_category(self):
        """Test handling scheduling with an inactive category."""
        input_data = {
            'organization': self.organization_active.id,
            'category': self.category_inactive.id,
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."

    def test_duplicate_appointment(self):
        """Test handling scheduling with a duplicate appointment."""
        input_data = {
            'organization': self.organization_active.id,
            'category': self.category_active.id,
            'user': self.user.id
        }
        # Create a duplicate appointment
        Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            is_scheduled=False
        )
        
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter due to duplicate
        assert msg == "Appointment already exists."

    def test_organization_not_found(self):
        """Test scheduling with a non-existing organization ID."""
        input_data = {
            'organization': 9999,  # Non-existing organization
            'category': self.category_active.id,
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Organization does not exist or is not accepting appointments."

    def test_category_not_found(self):
        """Test scheduling with a non-existing category ID."""
        input_data = {
            'organization': self.organization_active.id,
            'category': 9999,  # Non-existing category
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."

    def test_scheduling_for_different_user(self):
        """Test scheduling for a different user with a valid appointment."""
        another_user = User.objects.create_user(username="anotheruser", password="anotherpassword")
        input_data = {
            'organization': self.organization_active.id,
            'category': self.category_active.id,
            'user': another_user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is not None  # Expect a valid counter
        assert msg is None  # No error message

    def test_multiple_active_categories(self):
        """Test scheduling with multiple active categories for the same organization."""
        another_category = Category.objects.create(
            organization=self.organization_active,
            status="active",
            created_by=self.user
        )

        input_data = {
            'organization': self.organization_active.id,
            'category': another_category.id,
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is not None  # Expect a valid counter
        assert msg is None  # No error message

    def test_active_organization_no_categories(self):
        """Test handling scheduling when the organization is active but has no categories."""
        empty_organization = Organization.objects.create(
            name="Empty Organization",
            created_by=self.user,
            status="active"
        )
        input_data = {
            'organization': empty_organization.id,
            'category': self.category_active.id,
            'user': self.user.id
        }
        counter, msg = handle_appointment_scheduling(input_data)
        assert counter is None  # Expect no counter
        assert msg == "Category does not exist or is not accepting appointments."