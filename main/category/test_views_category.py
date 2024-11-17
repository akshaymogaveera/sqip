import pytest
from django.urls import reverse
from rest_framework import status
from main.models import Category, Organization
from rest_framework.test import APIClient
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestCategoryViewSet:
    @pytest.fixture(autouse=True)
    def setup(self, django_user_model):
        # Create a test client
        self.client = APIClient()
        # Create a test user
        self.user = django_user_model.objects.create_user(
            username="testuser", password="testpassword"
        )

        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create some test organizations
        self.org1 = Organization.objects.create(
            name="Arteria",
            city="New York",
            country="USA",
            state="NY",
            type="clinic",
            status="active",
            created_by=self.user
        )
        self.org2 = Organization.objects.create(
            name="Tech Co",
            city="San Francisco",
            country="USA",
            state="CA",
            type="company",
            status="inactive",
            created_by=self.user
        )

        # Create some test categories
        self.category1 = Category.objects.create(
            name="Consultation",
            type="general",
            status="active",
            organization=self.org1,
            created_by=self.user
        )
        self.category2 = Category.objects.create(
            name="Follow-up",
            type="general",
            status="inactive",
            organization=self.org1,
            created_by=self.user
        )
        self.category3 = Category.objects.create(
            name="Consultation",
            type="general",
            status="active",
            organization=self.org2,
            created_by=self.user
        )

    def test_filter_by_single_organization(self):
        url = f"{reverse('categories-list')}?organization=1"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert all(cat["organization"] == self.org1.id for cat in response.data["results"])

    def test_filter_by_multiple_organizations(self):
        url = f"{reverse('categories-list')}?organization=1,2"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3
        assert any(cat["organization"] == self.org1.id for cat in response.data["results"])
        assert any(cat["organization"] == self.org2.id for cat in response.data["results"])

    def test_filter_by_invalid_organization(self):
        url = f"{reverse('categories-list')}?organization=999"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_filter_by_status(self):
        url = f"{reverse('categories-list')}?status=active"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        for cat in response.data["results"]:
            assert cat["status"] == "active", f"Found status {cat['status']} instead of active"


    def test_filter_by_type(self):
        url = f"{reverse('categories-list')}?type=general"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_filter_by_name_contains_partial_match(self):
        url = f"{reverse('categories-list')}?name=Consultation"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3  # Adjust based on actual data


    def test_invalid_filter_by_organization(self):
        url = f"{reverse('categories-list')}?organization=9999"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # No categories should be returned


    def test_empty_filter_by_organization(self):
        url = f"{reverse('categories-list')}?organization="
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_invalid_filter_by_str_type_organization(self):
        url = f"{reverse('categories-list')}?organization=nonexistent"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid organization ID format" in response.data["detail"]


@pytest.mark.django_db
class TestCategoryByUserViewSet:
    @pytest.fixture(autouse=True)
    def setup(self, django_user_model):
        # Set up a test client and a test user with authentication.
        self.client = APIClient()
        self.user = django_user_model.objects.create_user(
            username="testuser", password="testpassword"
        )

        # Obtain a token for authentication.
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "testuser", "password": "testpassword"},
        )
        self.token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create three groups that will be associated with categories.
        self.group1 = Group.objects.create(name="Consultation Group")
        self.group2 = Group.objects.create(name="Surgery Group")
        self.group3 = Group.objects.create(name="Checkup Group")

        # Add the test user to "Consultation Group" (group1).
        self.user.groups.add(self.group1)

        # Create an organization for testing.
        self.org1 = Organization.objects.create(
            name="Arteria",
            city="New York",
            country="USA",
            state="NY",
            type="clinic",
            status="active",
            created_by=self.user
        )

        # Create categories and associate them with the respective groups.
        self.category1 = Category.objects.create(
            name="Consultation",
            type="general",
            status="active",
            organization=self.org1,
            group=self.group1,
            created_by=self.user
        )
        self.category2 = Category.objects.create(
            name="Surgery",
            type="specialized",
            status="inactive",
            organization=self.org1,
            group=self.group2,
            created_by=self.user
        )
        self.category3 = Category.objects.create(
            name="General Checkup",
            type="general",
            status="active",
            organization=self.org1,
            group=self.group3,
            created_by=self.user
        )

    def test_user_categories_with_associated_groups(self):
        """
        Test that a user can access only the categories associated with the groups they belong to.
        """
        url = reverse("categories-user")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # User is part of group1, so only categories linked to group1 should be returned.
        assert len(response.data["results"]) == 1  
        assert response.data["results"][0]["name"] == "Consultation"

    def test_user_categories_with_no_groups(self, django_user_model):
        """
        Test that a user with no groups does not have any categories to access.
        """
        # Create a user without any group associations.
        user_without_groups = django_user_model.objects.create_user(
            username="nogroupsuser", password="testpassword"
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "nogroupsuser", "password": "testpassword"},
        )
        token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Ensure that the user gets an empty list as they belong to no groups.
        url = reverse("categories-user")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # No categories should be returned

    def test_user_categories_with_no_associated_categories(self):
        """
        Test that if categories associated with the user's group are deleted, the user has no categories to access.
        """
        # Delete categories linked to group1 (which the user belongs to).
        Category.objects.filter(group=self.group1).delete()

        # Verify that the user can no longer access categories associated with their group.
        url = reverse("categories-user")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # No categories should be returned

    def test_user_categories_with_filters(self):
        """
        Test that the user can filter categories by status (e.g., only active categories).
        """
        url = f"{reverse('categories-user')}?status=active"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Only active category should be returned for the user.
        assert len(response.data["results"]) == 1  
        assert response.data["results"][0]["name"] == "Consultation"

    def test_user_cannot_access_categories_of_other_groups(self):
        """
        Test that a user can only access categories linked to groups they are part of and cannot access categories from other groups.
        """
        url = reverse("categories-user")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # User should not be able to access categories from group2 and group3.
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Consultation"  # Categories from other groups (Surgery, Checkup) should not appear.
