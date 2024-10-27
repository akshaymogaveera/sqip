import pytest
from main.models import Appointment, Organization, Category, User, Group
from main.service import (
    check_organization_is_active,
    check_category_is_active,
    check_user_exists,
    check_duplicate_appointment,
    get_last_counter_for_appointment,
)

@pytest.mark.django_db
class TestUtilityFunctions:
    
    def setup_method(self):
        """Set up data for testing."""
        # Create a user and group for the organization
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.group = Group.objects.create(name="Test Group")
        
        # Create an active organization associated with the user and group
        self.organization_active = Organization.objects.create(
            name="Test Organization",
            created_by=self.user,
            portfolio_site="",
            display_picture=None,
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",
            status="active",
            group=self.group
        )

        # Create an inactive organization for testing inactive scenarios
        self.organization_inactive = Organization.objects.create(
            name="Inactive Organization",
            created_by=self.user,
            portfolio_site="",
            display_picture=None,
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",
            status="inactive",
            group=self.group
        )

        # Create an active category associated with the active organization
        self.category_active = Category.objects.create(
            organization=self.organization_active,
            status="active",
            type="general",
            created_by=self.user
        )

        # Create an inactive category for testing inactive scenarios
        self.category_inactive = Category.objects.create(
            organization=self.organization_active,
            status="inactive",
            type="general",
            created_by=self.user
        )

        # Create an active appointment
        self.appointment_active = Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            status="active",
            counter=1
        )
    
    # The tests for each utility function follow here
    def test_check_organization_is_active(self):
        """Test if the organization is active and exists."""
        # Test for active organization
        assert check_organization_is_active(self.organization_active.id) == self.organization_active
        
        # Test for inactive organization
        assert check_organization_is_active(self.organization_inactive.id) is None
        
        # Test for non-existing organization
        assert check_organization_is_active(9999) is None

    def test_check_category_is_active(self):
        """Test if the category is active and exists."""
        # Test for active category
        assert check_category_is_active(self.category_active.id) == self.category_active
        
        # Test for inactive category
        assert check_category_is_active(self.category_inactive.id) is None
        
        # Test for non-existing category
        assert check_category_is_active(9999) is None
    
    def test_check_user_exists(self):
        """Test if the user exists."""
        # Test for existing user
        assert check_user_exists(self.user.id) == self.user
        
        # Test for non-existing user
        assert check_user_exists(9999) is None

    def test_check_duplicate_appointment(self):
        """Test if an active duplicate appointment exists."""
        # Test for existing duplicate appointment
        assert check_duplicate_appointment(
            self.user, self.organization_active, self.category_active
        ) is True
        
        # Test for non-existing duplicate appointment
        non_duplicate_category = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )
        assert check_duplicate_appointment(
            self.user, self.organization_active, non_duplicate_category
        ) is False

    def test_get_last_counter_for_appointment(self):
        """Test if the last counter for an appointment is retrieved correctly."""
        # Test for existing appointments
        assert get_last_counter_for_appointment(
            self.organization_active, self.category_active
        ) == 2  # Next counter after 1
        
        # Test for no previous appointments
        empty_category = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )
        assert get_last_counter_for_appointment(self.organization_active, empty_category) == 1