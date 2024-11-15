import pytest
from django.urls import reverse
from rest_framework import status
from main.models import Category, Organization
from rest_framework.test import APIClient

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
