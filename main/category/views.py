from django.shortcuts import get_object_or_404
from main.models import Category
from main.service import get_category
from main.category.serializers import CategorySerializer, ValidateCategorySerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from main.decorators import view_set_error_handler
import logging

logger = logging.getLogger('sqip')

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

    @view_set_error_handler
    def retrieve(self, request, pk=None):
        """
        Retrieve a single Category by ID.
        """
        category = get_object_or_404(Category, pk=pk)
        logger.info(
            "User %d (%s) retrieved category with ID %s.",
            request.user.id, request.user.username, pk
        )
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @view_set_error_handler
    def list(self, request):
        """
        List all categories with search, filter, and pagination support.
        """
        logger.info(
            "User %d (%s) is listing categories with filters: %s",
            request.user.id, request.user.username, request.query_params
        )
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.debug("Returning paginated response for categories.")
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @view_set_error_handler
    def create(self, request, *args, **kwargs):
        """Allow org-admins (with org_access) or staff to create categories for their organizations."""
        user = request.user
        data = request.data
        org_id = data.get('organization')
        if not org_id:
            return Response({'detail': 'organization is required'}, status=status.HTTP_400_BAD_REQUEST)

        # authorize
        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

            if not profile.is_org_admin or not profile.org_access.filter(id=org_id).exists():
                return Response({'detail': 'Unauthorized to create categories for this organization'}, status=status.HTTP_403_FORBIDDEN)

        # Ensure required fields are set server-side to avoid client errors.
        # Default status to 'active' if not supplied, and set created_by to the current user.
        # Build a mutable copy of the incoming data for serializer validation.
        try:
            incoming = {} if data is None else dict(data)
        except Exception:
            # Fallback for QueryDict-like objects
            incoming = {k: v for k, v in request.data.items()}

        if 'status' not in incoming or not incoming.get('status'):
            incoming['status'] = 'active'

        # Attach current user's id as created_by so serializer/model requirements are satisfied
        try:
            incoming['created_by'] = user.id
        except Exception:
            pass

        serializer = self.get_serializer(data=incoming)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
        except DjangoValidationError as e:
            # Return a clean 400 with validation messages from model.clean()/save()
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({'detail': ' '.join(msgs)}, status=status.HTTP_400_BAD_REQUEST)
        except DRFValidationError:
            # Let DRF handle serializer validation errors
            raise

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @view_set_error_handler
    def destroy(self, request, *args, **kwargs):
        """Allow org-admins (with org_access) or staff to delete categories for their organizations."""
        user = request.user
        pk = kwargs.get('pk')
        category = get_object_or_404(Category, pk=pk)

        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

            if not profile.is_org_admin or not profile.org_access.filter(id=category.organization_id).exists():
                return Response({'detail': 'Unauthorized to delete this category'}, status=status.HTTP_403_FORBIDDEN)

        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=["get"], url_path="active", permission_classes=[AllowAny], authentication_classes=[])
    @view_set_error_handler
    def active(self, request):
        """
        Custom action to list all active categories.
        """
        user_id = getattr(request.user, 'id', None)
        username = getattr(request.user, 'username', 'anonymous')
        logger.info("User %s (%s) is listing active categories.", user_id, username)
        active_categories = self.filter_queryset(self.get_queryset().filter(status="active"))
        page = self.paginate_queryset(active_categories)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.debug("Returning paginated response for active categories.")
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"], url_path="user")
    @view_set_error_handler
    def user(self, request):
        """
        Retrieve categories associated with the user's groups.
        Check the viewset description on how to use filter
        eg. ?status=active
        """
        user = request.user
        logger.info(
            "User %d (%s) is retrieving categories associated with their groups: %s",
            user.id, user.username, user.groups.all()
        )
        groups = user.groups.all()  # Get all groups the user belongs to

        # Assuming Category has a relation to Group via a ForeignKey or ManyToMany field
        queryset = self.filter_queryset(self.get_queryset().filter(group__in=groups))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    @action(detail=True, methods=["patch"], url_path="update-info")
    @view_set_error_handler
    def update_info(self, request, pk=None):
        """Update editable fields on a category (name, description, type, is_scheduled, etc).

        Intentionally does NOT allow changing group or organization.
        Authorized for staff/superuser or org-admins with org_access for this category's org.
        """
        category = get_object_or_404(Category, pk=pk)
        user = request.user

        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            if not (profile.is_org_admin and profile.org_access.filter(id=category.organization_id).exists()):
                return Response({'detail': 'Unauthorized to edit this category'}, status=status.HTTP_403_FORBIDDEN)

        # Only allow these fields — protect group and organization
        EDITABLE = {'name', 'description', 'type', 'is_scheduled', 'time_zone',
                    'opening_hours', 'break_hours', 'time_interval_per_appointment', 'max_advance_days'}
        payload = {k: v for k, v in (request.data or {}).items() if k in EDITABLE}
        if not payload:
            return Response({'detail': 'No editable fields provided'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(category, data=payload, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({'detail': ' '.join(msgs)}, status=status.HTTP_400_BAD_REQUEST)
        except DRFValidationError:
            raise

        logger.info("User %d (%s) updated info on category %s.", user.id, user.username, pk)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="update-status")
    @view_set_error_handler
    def update_status(self, request, pk=None):
        """
        Update the status of a category to active or inactive.
        """

        data = {
            "category_id": pk,
            "status": request.data.get("status")
        }
        serializer = ValidateCategorySerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        logger.info(
            "User %d (%s) is updating the status of category %s to %s.",
            request.user.id, request.user.username, pk, request.data.get("status")
        )
        category_id = serializer.validated_data["category_id"]
        new_status = serializer.validated_data["status"]

        category = get_category(category_id)

        # Update and save the category
        category.status = new_status
        try:
            category.save()
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({'detail': ' '.join(msgs)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            "Category %d status updated to %s by user %d (%s).",
            category_id, new_status, request.user.id, request.user.username
        )

        return Response(
            {"detail": f"Category status updated to {new_status}."},
            status=status.HTTP_200_OK,
        )
