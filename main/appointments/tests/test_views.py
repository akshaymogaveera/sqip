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

        self.group = Group.objects.create(name="Test Group for User")
        self.user.groups.add(self.group)

        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

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

        self.category_1 = Category.objects.create(
            organization=self.organization,
            status="active",
            type="online",
            created_by=self.user,
            group=self.group,
        )
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Create an appointment to use in check-in and cancel tests
        self.appointment = Appointment.objects.create(
            organization=self.organization,
            category=self.category_1,
            user=self.user,
            status="active",
            created_by=self.user,
            updated_by=self.user,
        )

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
        assert response.json() == {"user": ["User does not exist."]}

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
            status="inactive",
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
        assert response.json() == {
            "organization": ["Organization does not exist or is not active."]
        }

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
        assert response.json() == {
            "category": ["Category does not exist or is not active."]
        }

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
            status="active",
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
        assert "Category does not exist or is not accepting appointments." in str(
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
        assert response.json() == {
            "errors": {"appointment": ["Appointment already exists."]}
        }

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
        apppointment = Appointment.objects.get(id=response1.json().get("id"))
        assert response1.status_code == status.HTTP_201_CREATED
        assert apppointment.counter == 1  # Check that counter is set to 1

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
        apppointment = Appointment.objects.get(id=response2.json().get("id"))
        assert apppointment.counter == 2

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

        # Create a third appointment
        response2 = self.client.post(url, data, format="json")
        assert response2.status_code == status.HTTP_201_CREATED
        apppointment = Appointment.objects.get(id=response2.json().get("id"))
        assert apppointment.counter == 3

    def test_make_appointment_no_access(self):
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
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Unauthorized to access this appointment."}

    def test_make_appointment_with_admin_acess(self):
        """Test make appointment with admin access."""
        url = f'{reverse("appointments-list")}create/'

        self.user_new = User.objects.create_user(
            username="testuser4", password="testpassword", is_staff=True
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

    def test_make_appointment_with_group_admin_acess(self):
        """Test make appointment with group admin access."""
        url = f'{reverse("appointments-list")}create/'

        # Create group admin user
        group = Group.objects.create(name="Test Group Admin")
        user_group_admin = User.objects.create_user(
            username="testuser5", password="testpassword"
        )
        user_group_admin.groups.add(group)

        category_group = Category.objects.create(
            organization=self.organization,
            status="active",
            type="online",
            created_by=self.user,
            group=group,
        )

        # Create regular user
        test_new_user = User.objects.create_user(
            username="testuser6", password="testpassword"
        )

        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser5", "password": "testpassword"},
        )
        token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        data = {
            "organization": self.organization.id,
            "category": category_group.id,
            "user": test_new_user.id,
            "is_scheduled": False,
        }

        # Create a second appointment
        response = self.client.post(url, data, format="json")
        assert response.status_code == 201

    def test_check_in_success(self):
        """Test successfully checking in to an appointment."""
        url = reverse("appointments-check-in", args=[self.appointment.id])

        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()["detail"]
            == "Appointment status updated to 'checkin' successfully."
        )
        self.appointment.refresh_from_db()
        assert self.appointment.status == "checkin"

    def test_check_in_if_appt_creator(self):
        """Test check-in with an unauthorized user."""
        new_user = User.objects.create_user(
            username="unauthorized_user", password="testpassword"
        )
        self.client.force_authenticate(user=new_user)

        new_appt = Appointment.objects.create(
            organization=self.organization,
            category=self.category_1,
            user=new_user,
            status="active",
            created_by=self.user,
            updated_by=self.user,
        )

        url = reverse("appointments-check-in", args=[new_appt.id])
        response = self.client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Unauthorized to access this appointment."}
        self.appointment.refresh_from_db()
        assert self.appointment.status == "active"  # Status should remain unchanged

    def test_cancel_success(self):
        """Test successfully canceling an appointment."""
        url = reverse("appointments-cancel", args=[self.appointment.id])

        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()["detail"]
            == "Appointment status updated to 'cancel' successfully."
        )
        self.appointment.refresh_from_db()
        assert self.appointment.status == "cancel"

    def test_cancel_if_appt_creator(self):
        """Test cancel with an unauthorized user."""
        new_user = User.objects.create_user(
            username="unauthorized_user", password="testpassword"
        )
        self.client.force_authenticate(user=new_user)

        new_appt = Appointment.objects.create(
            organization=self.organization,
            category=self.category_1,
            user=new_user,
            status="active",
            created_by=self.user,
            updated_by=self.user,
        )

        url = reverse("appointments-cancel", args=[new_appt.id])
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()["detail"]
            == "Appointment status updated to 'cancel' successfully."
        )
        new_appt.refresh_from_db()
        assert new_appt.status == "cancel"

    def test_cancel_unauthorized_user(self):
        """Test canceling an appointment by an unauthorized user."""
        new_user = User.objects.create_user(
            username="unauthorized_user", password="testpassword"
        )
        self.client.force_authenticate(user=new_user)

        url = reverse("appointments-cancel", args=[self.appointment.id])
        response = self.client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Unauthorized to access this appointment."}
        self.appointment.refresh_from_db()
        assert self.appointment.status == "active"  # Status should remain unchanged

    def test_check_in_invalid_appointment(self):
        """Test check-in with a non-existing appointment."""
        url = reverse("appointments-check-in", args=[99999])  # Non-existing ID
        response = self.client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "non_field_errors": ["Appointment with this ID does not exist."]
        }

    def test_cancel_invalid_appointment(self):
        """Test canceling a non-existing appointment."""
        url = reverse("appointments-cancel", args=[99999])  # Non-existing ID
        response = self.client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "non_field_errors": ["Appointment with this ID does not exist."]
        }

    def test_check_in_staff_user(self):
        """Test check-in for a staff user with admin access."""
        # Log in as staff user
        self.client.logout()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpassword", is_staff=True
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "staffuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        url = reverse("appointments-check-in", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "detail": "Appointment status updated to 'checkin' successfully."
        }

    def test_check_in_superuser(self):
        """Test check-in for a superuser."""
        # Log in as superuser
        self.client.logout()
        self.superuser = User.objects.create_superuser(
            username="superuser", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "superuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        url = reverse("appointments-check-in", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "detail": "Appointment status updated to 'checkin' successfully."
        }

    def test_cancel_regular_user(self):
        """Test cancel for a regular user without admin access."""
        url = reverse("appointments-cancel", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "detail": "Appointment status updated to 'cancel' successfully."
        }

    def test_cancel_staff_user(self):
        """Test cancel for a staff user with admin access."""
        # Log in as staff user
        self.client.logout()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpassword", is_staff=True
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "staffuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        url = reverse("appointments-cancel", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "detail": "Appointment status updated to 'cancel' successfully."
        }

    def test_cancel_superuser(self):
        """Test cancel for a superuser."""
        # Log in as superuser
        self.client.logout()
        self.superuser = User.objects.create_superuser(
            username="superuser", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "superuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        url = reverse("appointments-cancel", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "detail": "Appointment status updated to 'cancel' successfully."
        }

    def teardown_method(self):
        """Clean up after each test if needed."""
        self.client.logout()


@pytest.mark.django_db
class TestMoveAppointment:
    def setup_method(self):
        # Initialize client and create user
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)

        # Create group, organization, and categories
        self.group = Group.objects.create(name="Test Group")
        self.user.groups.add(self.group)

        self.organization = Organization.objects.create(
            name="Test Organization", created_by=self.user, status="active"
        )

        self.category = Category.objects.create(
            organization=self.organization,
            status="active",
            created_by=self.user,
            group=self.group,
        )

        # Create initial appointments
        self.appointments = [
            Appointment.objects.create(
                organization=self.organization,
                category=self.category,
                user=self.user,
                counter=i,
                status="active",
                created_by=self.user,
                updated_by=self.user,
            )
            for i in range(1, 6)  # Appointments with counter values from 1 to 5
        ]

    def test_move_appointment_success(self):
        """Test successful appointment move."""
        url = reverse("appointments-move", args=[self.appointments[2].id])
        data = {"previous_appointment_id": self.appointments[0].id}

        response = self.client.post(url, data, format="json")

        # Refresh data to validate changes
        self.appointments[2].refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert self.appointments[2].counter == self.appointments[0].counter + 1
        self._validate_unique_and_ordered_counters()

    def test_move_appointment_to_first_position(self):
        """Test moving an appointment to the first position."""
        url = reverse("appointments-move", args=[self.appointments[3].id])
        data = {"previous_appointment_id": None}

        response = self.client.post(url, data, format="json")

        # Refresh data to validate changes
        self.appointments[3].refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert self.appointments[3].counter == 1  # New first position
        self._validate_unique_and_ordered_counters()

    def test_move_appointment_to_last_position(self):
        """Test moving an appointment to the last position."""
        url = reverse("appointments-move", args=[self.appointments[1].id])
        last_appointment_id = self.appointments[-1].id
        data = {"previous_appointment_id": last_appointment_id}

        response = self.client.post(url, data, format="json")

        # Refresh data to validate changes
        self.appointments[1].refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert self.appointments[1].counter == len(self.appointments)
        self._validate_unique_and_ordered_counters()

    def test_move_appointment_invalid_previous_id(self):
        """Test moving an appointment with an invalid previous_appointment_id."""
        url = reverse("appointments-move", args=[self.appointments[2].id])
        data = {"previous_appointment_id": 9999}  # Non-existing ID

        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "non_field_errors": ["Appointment with this ID does not exist."]
        }

    def test_move_appointment_with_no_permission(self):
        """Test moving an appointment without proper permissions."""
        # Create a new user without access
        other_user = User.objects.create_user(username="otheruser", password="password")
        self.client.force_authenticate(user=other_user)

        url = reverse("appointments-move", args=[self.appointments[1].id])
        data = {"previous_appointment_id": self.appointments[0].id}

        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Unauthorized to access this appointment."}

    def test_move_appointment_if_pervious_and_current_id_is_same(self):
        """Test moving an appointment without providing previous_appointment_id."""
        url = reverse("appointments-move", args=[self.appointments[2].id])
        data = {"previous_appointment_id": self.appointments[2].id}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "non_field_errors": [
                "The current appointment ID cannot be the same as the previous appointment ID."
            ]
        }

    def _validate_unique_and_ordered_counters(self):
        """Utility method to validate unique, sequential counters."""
        appointments = Appointment.objects.order_by("counter")
        counters = [app.counter for app in appointments]
        expected_counters = list(range(1, len(counters) + 1))
        assert (
            counters == expected_counters
        ), f"Expected counters: {expected_counters}, but got: {counters}"
