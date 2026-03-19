import logging
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from main.models import Organization, Category, Profile
from django.contrib.auth.models import Group
from main.organization.serializers import OrganizationSerializer
from main.category.serializers import CategorySerializer
from main.decorators import view_set_error_handler
from django.contrib.auth import get_user_model
from main.service import get_category
from django.db import transaction, IntegrityError
import phonenumbers

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

    @action(detail=False, methods=['get'], url_path='active', permission_classes=[AllowAny], authentication_classes=[])
    @view_set_error_handler
    def active_organizations(self, request):
        """
        Custom action to retrieve all active organizations.
        """
        user_id = getattr(request.user, 'id', None)
        username = getattr(request.user, 'username', 'anonymous')
        logger.info("User %s (%s) is retrieving active organizations.", user_id, username)
        active_orgs = self.filter_queryset(self.get_queryset().filter(status='active'))
        page = self.paginate_queryset(active_orgs)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_orgs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='landing', permission_classes=[AllowAny], authentication_classes=[])
    @view_set_error_handler
    def landing(self, request, pk=None):
        """
        Public landing endpoint for QR-code / direct-link access.
        Returns org details + its active categories so the frontend can
        render a booking page without requiring the user to search first.

        No authentication required — the user will be prompted to log in
        when they actually attempt to book.
        """
        organization = get_object_or_404(Organization, pk=pk, status='active')
        org_serializer = OrganizationSerializer(organization)

        categories = Category.objects.filter(
            organization=organization, status='active'
        ).order_by('name')
        cat_serializer = CategorySerializer(categories, many=True)

        return Response({
            "organization": org_serializer.data,
            "categories": cat_serializer.data,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='categories')
    @view_set_error_handler
    def categories(self, request, pk=None):
        """List categories for this organization. Org-admins with access can see all categories for their orgs; staff/superuser see all."""
        org = get_object_or_404(Organization, pk=pk)
        user = request.user
        # staff/superuser can view
        if user.is_staff or user.is_superuser:
            qs = Category.objects.filter(organization=org).order_by('name')
        else:
            # org-admins with access
            try:
                profile = user.profile
            except Exception:
                profile = None
            if profile and getattr(profile, 'is_org_admin', False) and profile.org_access.filter(id=org.id).exists():
                qs = Category.objects.filter(organization=org).order_by('name')
            else:
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CategorySerializer(qs, many=True)

        # Also build a list of admin users who are members of any category group in this org
        org_groups = Group.objects.filter(categories__organization=org).distinct()
        # map group id -> category id for this org
        group_to_cat = {}
        for g in org_groups:
            # For a OneToOne reverse relation, g.categories is the Category instance (or raises),
            # so handle both object and manager cases defensively.
            try:
                cat_obj = getattr(g, 'categories', None)
                # If it's a manager/queryset, get first(), otherwise treat as object
                if hasattr(cat_obj, 'first'):
                    first_cat = cat_obj.first()
                else:
                    first_cat = cat_obj
                group_to_cat[g.id] = first_cat.id if first_cat is not None else None
            except Exception:
                group_to_cat[g.id] = None

        # users who are in any of these groups
        users_qs = get_user_model().objects.filter(groups__in=org_groups).distinct()
        admins = []
        for u in users_qs:
            # collect category ids for this user within this org
            gids = list(u.groups.filter(id__in=[g.id for g in org_groups]).values_list('id', flat=True))
            cat_ids = []
            for gid in gids:
                cid = group_to_cat.get(gid)
                if cid:
                    cat_ids.append(cid)
            # include basic profile info
            try:
                prof = u.profile
                phone = str(prof.phone_number) if getattr(prof, 'phone_number', None) else None
            except Exception:
                phone = None
            admins.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'email': u.email,
                'phone': phone,
                'category_ids': cat_ids,
            })

        return Response({'results': serializer.data, 'admins': admins}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='admins')
    @view_set_error_handler
    def admins(self, request, pk=None):
        """Return a list of admin users who are members of category-groups for this organization.

        This is a convenience endpoint for the frontend to fetch category-admins scoped to the org.
        """
        org = get_object_or_404(Organization, pk=pk)
        user = request.user
        # Authorization: staff/superuser or org-admin with access
        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if not (profile and getattr(profile, 'is_org_admin', False) and profile.org_access.filter(id=org.id).exists()):
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        org_groups = Group.objects.filter(categories__organization=org).distinct()
        # map group id -> category id
        group_to_cat = {}
        for g in org_groups:
            try:
                cat_obj = getattr(g, 'categories', None)
                if hasattr(cat_obj, 'first'):
                    first_cat = cat_obj.first()
                else:
                    first_cat = cat_obj
                group_to_cat[g.id] = first_cat.id if first_cat is not None else None
            except Exception:
                group_to_cat[g.id] = None

        users_qs = get_user_model().objects.filter(groups__in=org_groups).distinct()
        admins = []
        for u in users_qs:
            gids = list(u.groups.filter(id__in=[g.id for g in org_groups]).values_list('id', flat=True))
            cat_ids = []
            for gid in gids:
                cid = group_to_cat.get(gid)
                if cid:
                    cat_ids.append(cid)
            try:
                prof = u.profile
                phone = str(prof.phone_number) if getattr(prof, 'phone_number', None) else None
            except Exception:
                phone = None
            admins.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'email': u.email,
                'phone': phone,
                'category_ids': cat_ids,
            })

        return Response({'admins': admins}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='create-category-user')
    @view_set_error_handler
    def create_category_user(self, request, pk=None):
        """Create a new user and assign them to a category's group within this organization.

        Expected payload: { first_name, last_name, phone (optional), email (optional), category_id }
        Only org-admins with access, staff, or superusers can call this.
        """
        org = get_object_or_404(Organization, pk=pk)
        user = request.user
        # Authorization
        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if not (profile and getattr(profile, 'is_org_admin', False) and profile.org_access.filter(id=org.id).exists()):
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        # Support single category_id or multiple category_ids
        category_id = data.get('category_id')
        category_ids = data.get('category_ids')
        ids = []
        if category_ids and isinstance(category_ids, (list, tuple)) and len(category_ids) > 0:
            ids = [int(x) for x in category_ids]
        elif category_id:
            try:
                ids = [int(category_id)]
            except Exception:
                return Response({'detail': 'Invalid category_id'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'detail': 'category_id or category_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate all category ids belong to this org and collect Category objects
        categories = []
        for cid in ids:
            cat = get_category(cid)
            if not cat or cat.organization_id != org.id:
                return Response({'detail': f'Invalid category {cid} for this organization'}, status=status.HTTP_400_BAD_REQUEST)
            categories.append(cat)

        # Enforce organization-level max_config_users if set
        if getattr(org, 'max_config_users', None) is not None:
            # Count distinct users who are members of any category group for this org
            org_groups = Group.objects.filter(categories__organization=org).distinct()
            existing_admins_count = get_user_model().objects.filter(groups__in=org_groups).distinct().count()
            if existing_admins_count >= org.max_config_users:
                return Response({'detail': 'Organization has reached max_config_users limit'}, status=status.HTTP_400_BAD_REQUEST)

        # Build user creation payload
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        email = (data.get('email') or '').strip() or None
        phone = (data.get('phone') or '').strip() or None

        # Normalize phone (try E.164) and pre-check uniqueness to avoid DB IntegrityError
        phone_norm = None
        if phone:
            try:
                # Try to parse using phonenumbers. If the input lacks a leading +, parsing may still work with None.
                p = phonenumbers.parse(phone, None)
                if phonenumbers.is_valid_number(p):
                    phone_norm = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
                else:
                    # Keep original if not valid
                    phone_norm = phone
            except Exception:
                phone_norm = phone

            try:
                if Profile.objects.filter(phone_number=phone_norm).exists():
                    return Response({'detail': 'Phone number already in use'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                # If lookup fails for any reason, proceed and let DB enforce uniqueness
                pass

        User = get_user_model()
        try:
            with transaction.atomic():
                # Generate a unique username
                base = 'user' + (phone_norm[-6:] if phone_norm else (email.split('@')[0] if email else 'anon'))
                username = base
                suffix = 0
                while User.objects.filter(username=username).exists():
                    suffix += 1
                    username = f"{base}{suffix}"
                new_user = User.objects.create_user(username=username, email=email or '')
                new_user.first_name = first_name or ''
                new_user.last_name = last_name or ''
                new_user.set_unusable_password()
                new_user.save()

                # create profile (set phone at creation to avoid extra update)
                prof_kwargs = {'user': new_user}
                if phone_norm:
                    prof_kwargs['phone_number'] = phone_norm
                prof = Profile.objects.create(**prof_kwargs)

                # Assign groups from each category (support multiple groups per user)
                for category in categories:
                    if category.group:
                        new_user.groups.add(category.group)

        except IntegrityError as e:
            logger.exception('Integrity error creating category user: %s', e)
            return Response({'detail': 'Phone number already in use or integrity error'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Failed to create category user: %s', e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Return minimal created user info
        return Response({'id': new_user.id, 'username': new_user.username, 'first_name': new_user.first_name, 'last_name': new_user.last_name}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='update-category-user')
    @view_set_error_handler
    def update_category_user(self, request, pk=None):
        """Update a user's category assignments (and optionally basic details) within this organization.

        Expected payload: { user_id, category_ids: [..], first_name?, last_name?, email?, phone? }
        """
        org = get_object_or_404(Organization, pk=pk)
        user = request.user
        # Authorization
        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if not (profile and getattr(profile, 'is_org_admin', False) and profile.org_access.filter(id=org.id).exists()):
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        target_id = data.get('user_id')
        if not target_id:
            return Response({'detail': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = get_user_model().objects.get(id=int(target_id))
        except Exception:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # collect category ids
        category_ids = data.get('category_ids') or []
        if not isinstance(category_ids, (list, tuple)):
            return Response({'detail': 'category_ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        # validate categories belong to org
        valid_cats = Category.objects.filter(organization=org, id__in=category_ids)
        valid_ids = set(valid_cats.values_list('id', flat=True))

        # compute groups for requested categories
        groups_to_set = [c.group for c in valid_cats if c.group]

        try:
            with transaction.atomic():
                # Remove user's membership from any groups that belong to this org
                org_group_ids = list(Group.objects.filter(categories__organization=org).values_list('id', flat=True))
                if org_group_ids:
                    target.groups.remove(*org_group_ids)
                # Add requested ones
                for g in groups_to_set:
                    target.groups.add(g)

                # Optionally update basic fields
                changed = False
                if 'first_name' in data:
                    target.first_name = data.get('first_name') or ''
                    changed = True
                if 'last_name' in data:
                    target.last_name = data.get('last_name') or ''
                    changed = True
                if 'email' in data:
                    target.email = data.get('email') or ''
                    changed = True
                if changed:
                    target.save()

                # phone update on profile
                phone = data.get('phone')
                if phone is not None:
                    try:
                        prof = target.profile
                    except Exception:
                        prof = None
                    if prof:
                        # try normalize
                        phone_norm = phone
                        try:
                            p = phonenumbers.parse(phone, None)
                            if phonenumbers.is_valid_number(p):
                                phone_norm = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
                        except Exception:
                            pass
                        prof.phone_number = phone_norm
                        prof.save()

        except IntegrityError as e:
            logger.exception('Integrity error updating category user: %s', e)
            return Response({'detail': 'Integrity error updating user'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('Failed to update category user: %s', e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Updated'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='delete-category-user')
    @view_set_error_handler
    def delete_category_user(self, request, pk=None):
        """Delete a user created as a category admin within this organization.

        Expected payload: { user_id }
        """
        org = get_object_or_404(Organization, pk=pk)
        user = request.user
        # Authorization
        if not (user.is_staff or user.is_superuser):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if not (profile and getattr(profile, 'is_org_admin', False) and profile.org_access.filter(id=org.id).exists()):
                return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        target_id = data.get('user_id')
        if not target_id:
            return Response({'detail': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = get_user_model().objects.get(id=int(target_id))
        except Exception:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the user is part of this org's groups
        org_group_ids = list(Group.objects.filter(categories__organization=org).values_list('id', flat=True))
        if not target.groups.filter(id__in=org_group_ids).exists():
            return Response({'detail': 'User not a category admin for this organization'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Safe delete
                target.delete()
        except Exception as e:
            logger.exception('Failed to delete category user: %s', e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Deleted'}, status=status.HTTP_200_OK)
