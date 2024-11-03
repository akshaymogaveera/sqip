import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from main.models import Organization, Category, Appointment
from django.contrib.auth.models import User, Group


@pytest.mark.django_db
class TestListUserAppointments:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.organization = Organization.objects.create(
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
        
        self.category = Category.objects.create(
            organization=self.organization,
            status="active",
            type="general",
            created_by=self.user,
        )

        # Create scheduled and unscheduled appointments
        self.scheduled_appointment = Appointment.objects.create(
            user=self.user,
            organization=self.organization,
            category=self.category,
            is_scheduled=True,
            status="active"
        )
        
        self.unscheduled_appointment = Appointment.objects.create(
            user=self.user,
            organization=self.organization,
            category=self.category,
            is_scheduled=False,
            status="active"
        )

    def test_list_user_appointments_all(self):
        """Test retrieving all user appointments."""
        url = reverse("appointments-list")  # Adjust URL name as necessary
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("count") == 2  # Should return both appointments

    def test_list_user_appointments_scheduled(self):
        """Test retrieving only scheduled user appointments."""
        url = reverse("appointments-list") + '?status_filter=scheduled'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("count") == 1  # Should return only the scheduled appointment

    def test_list_user_appointments_unscheduled(self):
        """Test retrieving only unscheduled user appointments."""
        url = reverse("appointments-list") + '?status_filter=unscheduled'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("count") == 1  # Should return only the unscheduled appointment

    def test_list_user_appointments_invalid_status_filter(self):
        """Test handling of invalid status_filter value."""
        url = reverse("appointments-list") + '?status_filter=invalid'
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("count") == 2  # Invalid filter should return all appointments

    def test_list_user_appointments_no_appointments(self):
        """Test response when user has no appointments."""
        new_user = User.objects.create_user("newuser", password="newpassword")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "newuser", "password": "newpassword"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        url = reverse("appointments-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get("count") == 0  # No appointments should return an empty list

    def teardown_method(self):
        """Clean up after each test."""
        self.client.logout()


@pytest.mark.django_db
class TestListScheduledAppointments:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(
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
        self.organization.groups.add(self.group)
        
        self.category1 = Category.objects.create(
            organization=self.organization,
            status="active",
            type="general",
            created_by=self.user,
        )
        
        self.category2 = Category.objects.create(
            organization=self.organization,
            status="active",
            type="inperson",
            created_by=self.user,
        )

        self.appointment1 = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category1, is_scheduled=True, status="active"
        )
        self.appointment2 = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category2, is_scheduled=True, status="active"
        )

        # Unscheduled appointments
        self.unscheduled_appointment = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category1, is_scheduled=False, status="active"
        )

    def test_list_scheduled_filter_by_multiple_category_ids(self):
        """Test filtering by multiple category_ids in list_scheduled."""
        url = f"{reverse('appointments-list-scheduled')}?category_id[]={self.category1.id}&category_id[]={self.category2.id}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2  # Should return both appointments

    def test_list_scheduled_superuser_access(self):
        """Test superuser can access all scheduled appointments."""
        User.objects.create_superuser("superuser", "super@test.com", "superpass")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "superuser", "password": "superpass"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        url = reverse("appointments-list-scheduled")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1  # Superuser should see all scheduled appointments

    def test_list_scheduled_staff_access(self):
        """Test staff can access all scheduled appointments."""
        staff_user = User.objects.create_user("staffuser", password="staffpass", is_staff=True)
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "staffuser", "password": "staffpass"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        url = reverse("appointments-list-scheduled")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1  # Staff should see all scheduled appointments

    def test_list_scheduled_default_regular_user_access(self):
        """Test default regular user."""
        # Assume self.user is a group admin
        url = reverse("appointments-list-scheduled")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_list_scheduled_regular_user_access(self):
        """Test regular user with no admin rights can only access their own appointments."""
        User.objects.create_user("regularuser", password="regularpass")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "regularuser", "password": "regularpass"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        url = reverse("appointments-list-scheduled")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # Regular user shouldn't see other users' appointments

    def test_list_scheduled_filter_by_category(self):
        """Test filtering by category_id in list_scheduled."""
        url = f"{reverse('appointments-list-scheduled')}?category_id={self.category1.id}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1  # Filter should return only matching category appointments

    def test_list_scheduled_invalid_category_id(self):
        """Test filtering by an invalid category_id returns no appointments."""
        url = f"{reverse('appointments-list-scheduled')}?category_id=9999"  # Non-existent category ID
        response = self.client.get(url)
        assert response.status_code == 400
        assert response.json() == {'category_id': ['One or more category IDs are invalid.']}

    def test_list_scheduled_with_group_access(self):
        """Test that a user can see appointments if they belong to the group."""
        # Create a new user and assign them to a group
        group_user = User.objects.create_user(username="group_user", password="testpassword")
        group = Group.objects.create(name="Test Group for User")
        group_user.groups.add(group)

        # Log in the group user
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "group_user", "password": "testpassword"},
        )
        group_user_token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {group_user_token}")

        # Create a new organization and category
        organization = Organization.objects.create(
            name="Group Organization",
            created_by=self.user,
            portfolio_site="",
            display_picture=None,
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",
            status="active",
        )

        organization.groups.add(group)

        category = Category.objects.create(
            organization=organization,
            status="active",
            type="general",
            created_by=self.user,
            group = group
        )

        # Create an appointment for the other user within the group
        Appointment.objects.create(
            user=self.user,
            category=category,
            organization=organization,
            is_scheduled=True,
            status="active",
            estimated_time="2024-12-31T10:00:00Z",  # Example future time
        )

        # Make a request to the list_scheduled endpoint
        url = reverse("appointments-list-scheduled")
        response = self.client.get(url)

        # Check if the response status is OK and contains the expected appointment
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json().get("results")) == 1



    def teardown_method(self):
        """Clean up after each test."""
        self.client.logout()



@pytest.mark.django_db
class TestListUnscheduledAppointments:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(
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
        self.organization.groups.add(self.group)
        
        self.category1 = Category.objects.create(
            organization=self.organization,
            status="active",
            type="general",
            created_by=self.user,
            group=self.group
        )
        
        self.category2 = Category.objects.create(
            organization=self.organization,
            status="active",
            type="inperson",
            created_by=self.user,
        )

        # Unscheduled appointments
        self.unscheduled_appointment1 = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category1, is_scheduled=False, status="active"
        )
        self.unscheduled_appointment2 = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category2, is_scheduled=False, status="active"
        )

        # scheduled appointments
        self.unscheduled_appointment = Appointment.objects.create(
            user=self.user, organization=self.organization,
            category=self.category1, is_scheduled=True, status="active"
        )

    def test_list_unscheduled_with_group_access(self):
        """Test that a user can see unscheduled appointments if they belong to the group."""
        # Create a new user and assign them to the group
        group_user = User.objects.create_user(username="group_user", password="testpassword")
        group_user.groups.add(self.group)

        # Log in the group user
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "group_user", "password": "testpassword"},
        )
        group_user_token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {group_user_token}")

        # Create an unscheduled appointment associated with the group
        Appointment.objects.create(
            user=self.user,
            category=self.category1,
            organization=self.organization,
            is_scheduled=False,  # Unscheduled appointment
            status="active",
        )

        # Make a request to the unscheduled endpoint
        url = reverse("appointments-list-unscheduled")
        response = self.client.get(url)

        # Check if the response status is OK and contains the expected appointment
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2  # Should return all unscheduled appointments

    def test_list_unscheduled_invalid_category_id(self):
        """Test filtering by an invalid category_id returns no appointments."""
        url = f"{reverse('appointments-list-unscheduled')}?category_id=9999"  # Non-existent category ID
        response = self.client.get(url)
        assert response.status_code == 400
        assert response.json() == {'category_id': ['One or more category IDs are invalid.']}

    def test_list_unscheduled_regular_user_access(self):
        """Test regular user can only access their own unscheduled appointments."""
        User.objects.create_user("regularuser", password="regularpass")
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "regularuser", "password": "regularpass"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        url = reverse("appointments-list-unscheduled")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # Regular user shouldn't see other users' appointments
    
    def test_list_unscheduled_filter_by_category(self):
        """Test filtering by category_id in unscheduled list."""
        url = f"{reverse('appointments-list-unscheduled')}?category_id={self.category1.id}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1  # Should return only matching category unscheduled appointments

    
    def test_list_unscheduled_filter_by_multiple_category_ids(self):
        """Test filtering by multiple category_ids in unscheduled list."""
        url = f"{reverse('appointments-list-unscheduled')}?category_id[]={self.category1.id}&category_id[]={self.category2.id}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2  # Should return both unscheduled appointments

    def teardown_method(self):
        """Clean up after each test."""
        self.client.logout()
