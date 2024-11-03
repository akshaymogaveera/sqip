import pytest
from main.models import Appointment, Organization, Category, User, Group
from main.service import (
    are_valid_category_ids,
    check_organization_is_active,
    check_category_is_active,
    check_user_exists,
    check_duplicate_appointment,
    get_authorized_categories_for_user,
    get_last_counter_for_appointment,
    get_scheduled_appointments_for_superuser,
    get_scheduled_appointments_for_user,
    get_unscheduled_appointments_for_superuser,
    get_unscheduled_appointments_for_user,
    get_user_appointments,
)

@pytest.mark.django_db
class TestUtilityFunctions:
    
    def setup_method(self):
        """Set up data for testing."""
        # Create primary and secondary test users
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.other_user = User.objects.create_user(username="otheruser", password="password")

        # Create groups and assign the primary user to a group
        self.group = Group.objects.create(name="Test Group")
        self.other_group = Group.objects.create(name="Other Group")
        self.user.groups.add(self.group)
        self.user.groups.add(self.other_group)

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
        )
        self.organization_active.groups.add(self.group)

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
        )
        self.organization_inactive.groups.add(self.group)

        # Active and inactive categories within the active organization
        self.category_active = Category.objects.create(
            organization=self.organization_active,
            status="active",
            type="general",
            created_by=self.user,
            group=self.group
        )
        self.category_inactive = Category.objects.create(
            organization=self.organization_active,
            status="inactive",
            type="general",
            created_by=self.user
        )

        # Additional category in a different group to test group restrictions
        self.other_category_active = Category.objects.create(
            organization=self.organization_active,
            status="active",
            type="other",
            created_by=self.user,
            group=self.other_group
        )

        # Create active, unscheduled appointments for the primary user
        self.unscheduled_appointment_1 = Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            status="active",
            counter=1,
            is_scheduled=False
        )
        self.unscheduled_appointment_2 = Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            status="active",
            counter=2,
            is_scheduled=False
        )

        # Scheduled appointment for the primary user
        self.scheduled_appointment = Appointment.objects.create(
            organization=self.organization_active,
            category=self.category_active,
            user=self.user,
            status="active",
            is_scheduled=True,
            estimated_time="2024-11-05 14:30:00"
        )

        # Unscheduled appointment for a different user to test filtering by user
        self.unscheduled_other_user = Appointment.objects.create(
            organization=self.organization_active,
            category=self.other_category_active,
            user=self.other_user,
            status="active",
            counter=3,
            is_scheduled=False
        )

        # Create a superuser for tests requiring elevated privileges
        self.superuser = User.objects.create_superuser(username="superuser", password="superpassword")

        
    
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
        assert check_category_is_active(self.category_active.id, self.organization_active) == self.category_active

        # Test for active category if org not passed
        assert check_category_is_active(self.category_active.id) == self.category_active
        
        # Test for inactive category
        assert check_category_is_active(self.category_inactive.id, self.organization_active) is None
        
        # Test for non-existing category
        assert check_category_is_active(9999, self.organization_active) is None
    
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
        ) == 3  # Next counter after 2
        
        # Test for no previous appointments
        empty_category = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )
        assert get_last_counter_for_appointment(self.organization_active, empty_category) == 1


    def test_are_valid_category_ids(self):
        """Test if all category IDs are active."""
        valid_category = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user
        )
        invalid_category = Category.objects.create(
            organization=self.organization_active, status="inactive", created_by=self.user
        )

        assert are_valid_category_ids([valid_category.id]) is True  # Valid
        assert are_valid_category_ids([valid_category.id, invalid_category.id]) is False  # Mixed
        assert are_valid_category_ids([9999]) is False  # Non-existing

    def test_get_user_appointments(self):
        """Test retrieving appointments for a user."""
        # Active appointment for user
        user_appointments = get_user_appointments(self.user)
        assert len(user_appointments) == 3  # Should return the active appointment

        # Get unscheduled appointments
        unscheduled_appointments = get_user_appointments(self.user, is_scheduled=False)
        assert len(unscheduled_appointments) == 2  # There are no unscheduled appointments

        # Get scheduled appointments
        scheduled_appointments = get_user_appointments(self.user, is_scheduled=True)
        assert len(scheduled_appointments) == 1  # There are no unscheduled appointments

    def test_get_unscheduled_appointments_for_superuser(self):
        """Test retrieving unscheduled appointments for superuser."""

        appointments = get_unscheduled_appointments_for_superuser()
        assert len(appointments) == 3  # Should return the unscheduled appointment

    def test_get_authorized_categories_for_user(self):
        """Test retrieving authorized categories for a user."""
        
        categories = get_authorized_categories_for_user(self.user)
        assert len(categories) == 2
        
        # Test for a user without authorized categories
        unassigned_user = User.objects.create_user(username="unassigneduser", password="password")
        categories_unassigned = get_authorized_categories_for_user(unassigned_user)
        assert len(categories_unassigned) == 0  # Should return no categories

    def test_basic_unscheduled_retrieval(self):
        """Test retrieval of basic unscheduled appointments for a user."""
        appointments = get_unscheduled_appointments_for_user(self.user)
        assert len(appointments) == 3
        assert self.unscheduled_appointment_1 in appointments
        assert self.unscheduled_appointment_2 in appointments
        assert self.unscheduled_other_user in appointments

    def test_filter_by_category_id(self):
        """Test retrieval of unscheduled appointments filtered by specific category ID."""
        appointments = get_unscheduled_appointments_for_user(self.user, category_ids=[self.category_active.id])
        assert len(appointments) == 2
        assert self.unscheduled_appointment_1 in appointments
        assert self.unscheduled_appointment_2 in appointments

    def test_no_authorized_categories(self):
        """Test behavior when a user has no authorized categories, expecting no access to appointments."""
        new_user = User.objects.create_user(username="newuser", password="password")
        appointments = get_unscheduled_appointments_for_user(new_user)
        assert len(appointments) == 0  # No appointments should be accessible


    def test_multiple_unscheduled_across_categories(self):
        """Test retrieval of unscheduled appointments across multiple categories."""
        appointments = get_unscheduled_appointments_for_user(
            self.user, category_ids=[self.category_active.id, self.other_category_active.id]
        )
        assert len(appointments) == 3
        assert self.unscheduled_appointment_1 in appointments
        assert self.unscheduled_appointment_2 in appointments

    def test_multiple_groups_with_different_categories(self):
        """Test retrieval when user is in multiple groups with appointments across different categories."""
        # Create a new category and assign it to a different group for the user
        group2 = Group.objects.create(name="Another Group")
        category3 = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user, group=group2
        )
        self.user.groups.add(group2)

        # Create an additional unscheduled appointment in the new category for the user
        unscheduled_appointment_group2 = Appointment.objects.create(
            organization=self.organization_active,
            category=category3,
            user=self.user,
            is_scheduled=False,
            status="active"
        )

        appointments = get_unscheduled_appointments_for_user(self.user)
        assert len(appointments) == 4
        assert unscheduled_appointment_group2 in appointments

    def test_superuser_not_affected(self):
        """Ensure superuser has no impact on non-superuser queryset, expecting an empty result."""
        appointments = get_unscheduled_appointments_for_user(self.superuser)
        assert len(appointments) == 0  # Superuser should not have non-superuser appointments by default


    def test_basic_scheduled_retrieval(self):
        """Test retrieval of basic scheduled appointments for a user."""
        appointments = get_scheduled_appointments_for_user(self.user)
        assert len(appointments) == 1
        assert self.scheduled_appointment in appointments

    def test_filter_by_category_id_for_scheduled(self):
        """Test retrieval of scheduled appointments filtered by specific category ID."""
        appointments = get_scheduled_appointments_for_user(self.user, category_ids=[self.category_active.id])
        assert len(appointments) == 1
        assert self.scheduled_appointment in appointments

    def test_no_authorized_categories_for_scheduled(self):
        """Test behavior when a user has no authorized categories, expecting no access to scheduled appointments."""
        new_user = User.objects.create_user(username="newuser", password="password")
        appointments = get_scheduled_appointments_for_user(new_user)
        assert len(appointments) == 0  # No appointments should be accessible

    def test_multiple_scheduled_across_categories(self):
        """Test retrieval of scheduled appointments across multiple categories."""
        appointments = get_scheduled_appointments_for_user(
            self.user, category_ids=[self.category_active.id, self.other_category_active.id]
        )
        assert len(appointments) == 1
        assert self.scheduled_appointment in appointments

    def test_multiple_groups_with_different_categories_for_scheduled(self):
        """Test retrieval when user is in multiple groups with appointments across different categories."""
        # Create a new category and assign it to a different group for the user
        group2 = Group.objects.create(name="Another Group")
        category3 = Category.objects.create(
            organization=self.organization_active, status="active", created_by=self.user, group=group2
        )
        self.user.groups.add(group2)

        # Create an additional scheduled appointment in the new category for the user
        scheduled_appointment_group2 = Appointment.objects.create(
            organization=self.organization_active,
            category=category3,
            user=self.user,
            is_scheduled=True,
            status="active",
            estimated_time="2024-11-05 15:00:00"
        )

        appointments = get_scheduled_appointments_for_user(self.user)
        assert len(appointments) == 2  # Expecting two scheduled appointments
        assert scheduled_appointment_group2 in appointments

    def test_superuser_can_access_scheduled(self):
        """Ensure superuser can access all scheduled appointments."""
        appointments = get_scheduled_appointments_for_superuser()
        assert len(appointments) >= 1  # Should include all scheduled appointments

    def test_no_scheduled_appointments(self):
        """Test when a user has no scheduled appointments, expecting an empty result."""
        # Remove all scheduled appointments for the user
        Appointment.objects.filter(user=self.user, is_scheduled=True).delete()
        appointments = get_scheduled_appointments_for_user(self.user)
        assert len(appointments) == 0

    def test_no_unscheduled_appointments(self):
        """Test when a user has no scheduled appointments, expecting an empty result."""
        # Remove all scheduled appointments for the user
        Appointment.objects.filter(is_scheduled=False).delete()
        appointments = get_unscheduled_appointments_for_user(self.user)
        assert len(appointments) == 0