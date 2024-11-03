import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from main.models import Organization, Category, Appointment
from django.contrib.auth.models import User, Group


@pytest.mark.django_db
class TestMakeAppointment:
    def setup_method(self):
        # Create a test client
        self.client = APIClient()
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create a test group if necessary
        self.group = Group.objects.create(name="Test Group")

        # Create an active organization and associate it with the created user
        self.organization = Organization.objects.create(
            name="Test Organization",
            created_by=self.user,  # Set the created_by field to the test user
            portfolio_site="",  # Add default or necessary values
            display_picture=None,  # Set to None if not testing image uploads
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",  # Choose a valid type from your TYPE choices
            status="active",  # Choose a valid status from your STATUS_CHOICES
        )
        self.organization.groups.add(self.group)
        # Create an active category
        self.category = Category.objects.create(
            organization=self.organization,
            status="active",
            type="general",
            created_by=self.user,
        )
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

    def test_make_appointment_success(self):
        """Test successfully creating an appointment."""
        url = f'{reverse("appointments-list")}create/'  # Replace with your actual URL name
        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.count() == 1
        assert Appointment.objects.get().user == self.user

    def test_make_appointment_user_not_found(self):
        """Test creating an appointment with a non-existing user."""
        url = f'{reverse("appointments-list")}create/'
        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": 99999,  # Non-existing user ID
            "is_scheduled": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {'errors': {'user': ['User does not exist.']}}

    def test_make_appointment_organization_not_active(self):
        """Test creating an appointment with a non-active organization."""
        inactive_organization = Organization.objects.create(
            name="Test Organization1",
            created_by=self.user,
            portfolio_site="",
            display_picture=None,
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",
            status="inactive"
        )
        inactive_organization.groups.add(Group.objects.create(name="Test Group1"))

        url = f'{reverse("appointments-list")}create/'
        data = {
            "organization": inactive_organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Organization does not exist or is not active." in str(
            response.data["errors"]
        )

    def test_make_appointment_category_not_active(self):
        """Test creating an appointment with a non-active category."""
        inactive_category = Category.objects.create(
            organization=self.organization,
            status="inactive",
            type="general",
            created_by=self.user,
        )

        url = f'{reverse("appointments-list")}create/'
        data = {
            "organization": self.organization.id,
            "category": inactive_category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Category does not exist or is not active." in str(
            response.data["errors"]
        )

    def test_make_appointment_category_with_wrong_org(self):
        """Test creating an appointment with wrong org."""

        dummy_organization = Organization.objects.create(
            name="Test Organization1",
            created_by=self.user,
            portfolio_site="",
            display_picture=None,
            city="Test City",
            state="Test State",
            country="Test Country",
            type="restaurant",
            status="active"
        )
        inactive_category = Category.objects.create(
            organization=dummy_organization,
            status="active",
            type="general",
            created_by=self.user,
        )

        url = f'{reverse("appointments-list")}create/'
        data = {
            "organization": self.organization.id,
            "category": inactive_category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Category does not exist or is not accepting appointments.' in str(
            response.data["errors"]
        )

    def test_make_appointment_duplicate(self):
        """Test creating a duplicate appointment."""
        url = f'{reverse("appointments-list")}create/'
        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        # Create the first appointment
        self.client.post(url, data, format="json")

        # Attempt to create a duplicate
        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {'errors': {'appointment': ['Appointment already exists.']}}

    def test_make_appointment_counter_increment(self):
        """Test that the counter is incremented correctly for new appointments."""
        url = f'{reverse("appointments-list")}create/'

        # Create the first appointment
        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }
        response1 = self.client.post(url, data, format="json")

        assert response1.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.count() == 1
        assert Appointment.objects.get().counter == 1  # Check that counter is set to 1

        self.user = User.objects.create_user(
            username="testuser1", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser1", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        # Create a second appointment
        response2 = self.client.post(url, data, format="json")
        assert response2.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.count() == 2
        assert (
            Appointment.objects.latest("id").counter == 2
        )  # Check that counter is incremented to 2

        self.user = User.objects.create_user(
            username="testuser3", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser3", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        # Create a second appointment
        response2 = self.client.post(url, data, format="json")
        assert response2.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.count() == 3
        assert (
            Appointment.objects.latest("id").counter == 3
        )  # Check that counter is incremented to 2

    def test_make_appointment_no_acess(self):
        """Test make appointment if no access."""
        url = f'{reverse("appointments-list")}create/'

        self.user_new = User.objects.create_user(
            username="testuser4", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser4", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        # Create a second appointment
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {'errors': {'user': ['You are not allowed to create an appointment for this user.']}}

    def test_make_appointment_with_admin_acess(self):
        """Test make appointment with admin access."""
        url = f'{reverse("appointments-list")}create/'

        self.user_new = User.objects.create_user(
            username="testuser4", password="testpassword", is_staff = True
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser4", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        data = {
            "organization": self.organization.id,
            "category": self.category.id,
            "user": self.user.id,
            "is_scheduled": False,
        }

        # Create a second appointment
        response = self.client.post(url, data, format="json")
        assert response.status_code == 201

    def teardown_method(self):
        """Clean up after each test if needed."""
        self.client.logout()
