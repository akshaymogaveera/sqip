import logging
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from main.models import Organization
from main.organization.serializers import OrganizationSerializer
from main.decorators import view_set_error_handler

logger = logging.getLogger('sqip')

class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for consistent results per page.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class OrganizationFilter(FilterSet):
    """
    Custom filter for organizations to enable case-insensitive filtering on specific fields.
    """
    name = CharFilter(field_name='name', lookup_expr='icontains')
    city = CharFilter(field_name='city', lookup_expr='icontains')
    country = CharFilter(field_name='country', lookup_expr='icontains')
    state = CharFilter(field_name='state', lookup_expr='icontains')

    class Meta:
        model = Organization
        fields = ['status', 'type', 'city', 'state', 'country', 'name']  # List of fields to filter on

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing Organization instances with search, filter, 
    ordering, and pagination capabilities.

    ### Filter Examples
    - `?status=active` - Filters organizations by status.
    - `?type=clinic` - Filters organizations by type, such as `clinic`.
    - `?city=New York` - Case-insensitive search by city name containing `New York`.
    - `?country=Canada` - Case-insensitive search by country containing `Canada`.
    - `?name=Arteria` - Case-insensitive search by organization name containing `Arteria`.

    ### Search Example
    - `?search=tech` - Searches across name, city, state, country, and type fields for matches with `tech`.

    ### Ordering Examples
    - `?ordering=name` - Orders organizations by name (ascending).
    - `?ordering=-name` - Orders organizations by name (descending).
    - `?ordering=city` - Orders organizations by city.
    - `?ordering=state,-country` - Orders organizations by state (ascending) and country (descending).

    ### Pagination Examples
    - `?page=1` - Returns the first page of results.
    - `?page_size=5` - Adjusts the number of items per page (default is 10, maximum is 100).

    ### Endpoint Examples
    - **Retrieve specific organization by ID**: `/organizations/<id>/`
    - **List organizations with filters, search, and pagination**: `/organizations/?status=active&type=clinic&city=New York`
    - **Custom action for active organizations**: `/organizations/active/` (lists organizations with `status=active`)

    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrganizationFilter
    search_fields = ['name', 'city', 'state', 'country', 'type']
    ordering_fields = ['name', 'created_by', 'city', 'state', 'country']
    ordering = ['name']  # Default ordering by name

    @view_set_error_handler
    def retrieve(self, request, pk=None):
        """
        Retrieve a single Organization by ID.
        """
        logger.info("User %d (%s) is retrieving organization with ID %s.", request.user.id, request.user.username, pk)
        organization = get_object_or_404(Organization, pk=pk)
        serializer = self.get_serializer(organization)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @view_set_error_handler
    def list(self, request):
        """
        List all organizations with search, filter, and pagination support.
        """
        logger.info("User %d (%s) is listing organizations with filters: %s", request.user.id, request.user.username, request.query_params)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.debug("Returning paginated response for organizations.")
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='active')
    @view_set_error_handler
    def active_organizations(self, request):
        """
        Custom action to retrieve all active organizations.
        """
        logger.info("User %d (%s) is retrieving active organizations.", request.user.id, request.user.username)
        active_orgs = self.filter_queryset(self.get_queryset().filter(status='active'))
        page = self.paginate_queryset(active_orgs)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_orgs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
