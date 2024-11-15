from django.shortcuts import get_object_or_404
from main.models import Category
from main.category.serializers import CategorySerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for consistent results per page.
    """
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow clients to adjust page size
    max_page_size = 100  # Limit the maximum page size

    
class CategoryFilter(FilterSet):
    organization = CharFilter(method='filter_by_organization')
    status = CharFilter(field_name='status', lookup_expr='iexact')
    type = CharFilter(field_name='type', lookup_expr='iexact')
    description = CharFilter(field_name='description', lookup_expr='icontains')

    class Meta:
        model = Category
        fields = ['status', 'type', 'description', 'organization']

    def filter_by_organization(self, queryset, name, value):
        # Try converting the value to a list of integers
        try:
            # If value is a single organization ID or a comma-separated list
            if isinstance(value, str):
                organization_ids = [int(v) for v in value.split(',') if v.strip()]
            else:
                organization_ids = [int(value)]
            
            # Apply the filter
            return queryset.filter(organization_id__in=organization_ids)
        except ValueError:
            # Return a 400 response if the conversion fails
            raise ValidationError({"detail": "Invalid organization ID format. Expected integer values."})
    
    

class CategoryViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing Category instances with search, filter, 
    ordering, and pagination capabilities.

    ### Filter Examples
    - `?status=active` - Filters categories by status.
    - `?type=general` - Filters categories by type, such as `general`.
    - `?description=consultation` - Case-insensitive search by description containing `consultation`.
    - `?organization=<organization_id>` - Filters categories by a specific organization ID.
    - `?organization=<org_id1>,<org_id2>` - Filters categories by a list of organization IDs.

    ### Search Example
    - `?search=general` - Searches within description field for matches with `general`.

    ### Ordering Examples
    - `?ordering=created_at` - Orders categories by creation date (ascending).
    - `?ordering=-status` - Orders categories by status (descending).

    ### Pagination Examples
    - `?page=1` - Returns the first page of results.
    - `?page_size=5` - Adjusts the number of items per page (default is 10, maximum is 100).

    ### Endpoint Examples
    - **Retrieve specific category by ID**: `/categories/<id>/`
    - **List categories with filters, search, and pagination**: `/categories/?status=active&type=general&description=consultation`
    - **List categories filtered by organization ID**: `/categories/?organization=1`
    - **List categories filtered by multiple organization IDs**: `/categories/?organization=1,2,3`
    - **Custom action for active categories**: `/categories/active/` (lists categories with `status=active`)
    """


    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter  # Assign the filter here
    search_fields = ['description']
    ordering_fields = ['created_at', 'estimated_time']
    ordering = ['created_at']

    def retrieve(self, request, pk=None):
        """
        Retrieve a single Category by ID.
        """
        category = get_object_or_404(Category, pk=pk)
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request):
        """
        List all categories with search, filter, and pagination support.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """
        Custom action to list all active categories.
        """
        active_categories = self.filter_queryset(self.get_queryset().filter(status="active"))
        page = self.paginate_queryset(active_categories)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
