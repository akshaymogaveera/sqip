import pytest
from django.urls import reverse
from rest_framework import status
from main.models import Organization
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestOrganizationViewSet:
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

        # Create some test data
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
        # Additional active organizations for pagination tests
        self.active_orgs = [
            Organization.objects.create(
                name=f"Active Org {i}",
                city="City A",
                country="Country A",
                state="State A",
                type="store",
                status="active",
                created_by=self.user
            ) for i in range(5)
        ]

    def test_retrieve_organization(self):
        url = reverse("organizations-detail", args=[self.org1.id])
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.org1.name

    def test_list_organizations(self):
        url = reverse("organizations-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2

    def test_filter_by_status(self):
        url = f"{reverse('organizations-list')}?status=active"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert all(org['status'] == 'active' for org in response.data["results"])

    def test_filter_by_type(self):
        url = f"{reverse('organizations-list')}?type=clinic"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["type"] == "clinic"

    def test_case_insensitive_search(self):
        url = f"{reverse('organizations-list')}?search=arteria"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"].lower() == "arteria"

    def test_filter_multiple_fields(self):
        url = f"{reverse('organizations-list')}?city=New York&type=clinic"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["city"] == "New York"

    def test_ordering_by_multiple_fields(self):
        url = f"{reverse('organizations-list')}?ordering=state,-city"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        states = [org["state"] for org in response.data["results"]]
        cities = [org["city"] for org in response.data["results"]]
        assert states == sorted(states)
        assert cities[0] == "San Francisco"

    def test_invalid_filter(self):
        url = f"{reverse('organizations-list')}?status=nonexistent"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {'status': ['Select a valid choice. nonexistent is not one of the available choices.']}

    def test_invalid_ordering_field(self):
        url = f"{reverse('organizations-list')}?ordering=nonexistent_field"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_active_organizations_endpoint(self):
        url = reverse("organizations-active-organizations")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert all(org['status'] == 'active' for org in response.data["results"])

    def test_active_with_invalid_filter(self):
        url = f"{reverse('organizations-active-organizations')}?type=nonexistent"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() ==  {'type': ['Select a valid choice. nonexistent is not one of the available choices.']}

    def test_active_organizations_ordered(self):
        url = f"{reverse('organizations-active-organizations')}?ordering=city"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        cities = [org["city"] for org in response.data["results"]]
        assert cities == sorted(cities)

    def test_pagination_on_active_organizations(self):
        url = f"{reverse('organizations-active-organizations')}?page_size=2"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2  # Should return 2 results per page
        assert "next" in response.data

    def test_pagination_next_page(self):
        url = f"{reverse('organizations-list')}?page=2&page_size=1"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1  # Should return one item on page 2
        assert "next" in response.data

    def test_filter_by_name_contains_partial_match(self):
        url = f"{reverse('organizations-list')}?name=Tech"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Tech Co"

    def test_empty_search_results(self):
        """Test search query with no matching results."""
        url = f"{reverse('organizations-list')}?search=Nonexistent"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_filter_on_multiple_fields_with_no_results(self):
        """Test multiple filters that return no results."""
        url = f"{reverse('organizations-list')}?type=bank&city=Tokyo"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_ordering_mixed_asc_desc(self):
        """Test ordering by multiple fields with mixed ascending and descending."""
        url = f"{reverse('organizations-list')}?ordering=city,-name"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        cities = [org["city"] for org in response.data["results"]]
        names = [org["name"] for org in response.data["results"]]
        assert cities == sorted(cities)  # First field should be ascending
        assert names != sorted(names)    # Second field is descending

    def test_active_organizations_with_filter_and_search(self):
        """Test active organizations endpoint with additional filtering and search."""
        url = f"{reverse('organizations-active-organizations')}?search=Active&type=store"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0
        assert all(org["type"] == "store" for org in response.data["results"])
        assert all("Active" in org["name"] for org in response.data["results"])

    def test_active_organizations_pagination_exceeding_pages(self):
        """Test pagination on active organizations with a page number exceeding available pages."""
        url = f"{reverse('organizations-active-organizations')}?page=10"
        response = self.client.get(url)
        assert response.status_code == 404
        assert response.json() == {'detail': 'Invalid page.'}

    def test_search_and_filter_combination(self):
        """Test combined search and filter to narrow down results."""
        url = f"{reverse('organizations-list')}?search=tech&status=inactive&type=company"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Tech Co"

    def test_search_case_insensitive_mixed_case_query(self):
        """Test case-insensitive search with a mixed-case query."""
        url = f"{reverse('organizations-list')}?search=arTEria"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"].lower() == "arteria"

    def test_ordering_with_search(self):
        """Test ordering results that are returned by a search query."""
        url = f"{reverse('organizations-list')}?search=Org&ordering=-name"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        names = [org["name"] for org in response.data["results"]]
        assert names == sorted(names, reverse=True)  # Should be ordered by name descending

    def test_filter_with_blank_fields(self):
        """Test filter with blank optional fields (should ignore blanks)."""
        url = f"{reverse('organizations-list')}?name=Arteria&city=&state="
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Arteria"

    def test_invalid_filter_combination(self):
        """Test an invalid combination of filters returning empty result."""
        url = f"{reverse('organizations-list')}?type=restaurant&country=Japan"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0  # No match for type restaurant in Japan

    def test_filter_nonexistent_field(self):
        """Test attempting to filter on a field that doesn't exist."""
        url = f"{reverse('organizations-list')}?nonexistent_field=value"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_search_no_keyword(self):
        """Test empty search query (should return all results)."""
        url = f"{reverse('organizations-list')}?search="
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2  # All organizations should appear