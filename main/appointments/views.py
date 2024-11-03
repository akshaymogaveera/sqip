from main.appointments.service import handle_appointment_scheduling
from main.appointments.utils import update_appointment
from main.service import (
    get_scheduled_appointments_for_superuser,
    get_scheduled_appointments_for_user,
    get_unscheduled_appointments_for_superuser,
    get_unscheduled_appointments_for_user,
    get_user_appointments,
)
from main.verification.utils import check_if_user_is_authorized, check_user_in_group
from rest_framework.permissions import IsAuthenticated

from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from main.models import Appointment, Category, Organization, User
from main.appointments.serializers import (
    AppointmentSerializer,
    MakeAppointmentSerializer,
    OrganizationSerializer,
    ValidateAppointmentInput,
    AppointmentListQueryParamsSerializer
)
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AppointmentListCreateView(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        """Returns list of all User appointments.
        
        ?status_filter=all (default)
        ?status_filter=scheduled
        ?status_filter=unscheduled
        
        """
        user = self.request.user
        status_filter = request.query_params.get('status_filter', 'all')

        # Retrieve appointments based on the filter
        if status_filter == 'scheduled':
            appointments = get_user_appointments(user, is_scheduled=True)
        elif status_filter == 'unscheduled':
            appointments = get_user_appointments(user, is_scheduled=False)
        else:
            appointments = get_user_appointments(user)  # 'all' or invalid value

        # Paginate the queryset using StandardResultsSetPagination
        page = self.paginate_queryset(appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="scheduled")
    def list_scheduled(self, request):
        """List scheduled appointments for a user or superuser.
        
        if super_user or staff (very few users who control the application)
            Will be able to see all Appointments in the APP!
        else: Users that are Group Admin may have groups assigned to them.
            User
                - Groups: [Tim Hortons] - This group admin will be able to see all appointments under Tim Hortons.
        
        ** Recommended one group assigned to each user

        /appointments/scheduled/?category_id=1&category_id=2&category_id=3
        """
        user = self.request.user

        query_params_serializer = AppointmentListQueryParamsSerializer(data=request.query_params)
        query_params_serializer.is_valid(raise_exception=True)
        category_ids = query_params_serializer.validated_data.get("category_id", [])

        if user.is_superuser or user.is_staff:
            scheduled_appointments = get_scheduled_appointments_for_superuser(category_ids=category_ids)
        else:
            scheduled_appointments = get_scheduled_appointments_for_user(user, category_ids=category_ids)

        # Paginate the queryset using StandardResultsSetPagination
        page = self.paginate_queryset(scheduled_appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(scheduled_appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unscheduled")
    def list_unscheduled(self, request):
        """List unscheduled appointments for a user or superuser.
        
        if super_user or staff (very few users who control the application)
            Will be able to see all Appointments in the APP!
        else: Users that are Group Admin may have groups assigned to them.
            User
                - Groups: [Tim Hortons] - This group admin will be able to see all appointments under Tim Hortons.
        ** Recommended one group assigned to each user

        /appointments/unscheduled/?category_id=1&category_id=2&category_id=3
        """
        user = self.request.user

        query_params_serializer = AppointmentListQueryParamsSerializer(data=request.query_params)
        query_params_serializer.is_valid(raise_exception=True)
        category_ids = query_params_serializer.validated_data.get("category_id", [])

        print(category_ids, "-----------")

        if user.is_superuser or user.is_staff:
            unscheduled_appointments = get_unscheduled_appointments_for_superuser(category_ids=category_ids)
        else:
            unscheduled_appointments = get_unscheduled_appointments_for_user(user, category_ids=category_ids)

        # Paginate the queryset using StandardResultsSetPagination
        page = self.paginate_queryset(unscheduled_appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(unscheduled_appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="create")
    def make_appointment(self, request):
        """Make appointment
        a user or Admin(behalf of any user) can make an appointment.

        payload:

        {
            "organization": 1,
            "category": 1,
            "user":2,
            "is_scheduled": false
        }

        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_
        """
        # Input validation
        input_serializer = ValidateAppointmentInput(
            data=request.data, context={"request": request}
        )
        if not input_serializer.is_valid():
            return Response(
                {"errors": input_serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Main serializer validation
        serializer = MakeAppointmentSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if appointment is scheduled
        if not input_serializer.validated_data.get("is_scheduled"):
            counter, error_message = handle_appointment_scheduling(
                input_serializer.validated_data
            )

            if error_message:
                return Response(
                    {"errors": {"appointment": [error_message]}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Set counter for new appointment
            serializer.validated_data["counter"] = counter
        else:
            Response({"errors": "Yet to Implement"}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check_in")
    def check_in(self, request, pk=None):
        try:
            appointment = self.get_queryset().get(pk=pk, status="active")
            # get organization from appointment
            # check if the user is in organizations group (admin) else deny access

            # get group
            group = appointment.organization.group
            if not check_user_in_group(self.request.user, group):
                return Response({"detail": "Unauthorized."}, status=status.HTTP_200_OK)

            update_appointment(appointment, "checkin")

            return Response(
                {"detail": "Checked in successfully."}, status=status.HTTP_200_OK
            )
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        try:
            appointment = self.get_queryset().get(pk=pk, status="active")

            # get group
            group = appointment.organization.group
            if not check_if_user_is_authorized(self.request.user, appointment, group):
                return Response({"detail": "Unauthorized."}, status=status.HTTP_200_OK)

            update_appointment(appointment, "cancel")

            return Response(
                {"detail": "Cancelled successfully."}, status=status.HTTP_200_OK
            )
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        previous_id = request.data.get("previous", None)
        previous_counter = 0
        # get organization from appointment
        # check if the user is in organizations group (admin) else deny access
        try:
            appointment = self.get_queryset().get(pk=pk, status="active")

            # get group
            group = appointment.organization.group
            if not check_user_in_group(self.request.user, group):
                return Response({"detail": "Unauthorized."}, status=status.HTTP_200_OK)

            # update the appointment thats being removed
            update_appointment(
                appointment, "inactive", current_counter=appointment.counter
            )

            if previous_id is None:
                previous_appointment = Appointment.objects.filter(
                    organization=appointment.organization.id,
                    category=appointment.category.id,
                    status="active",
                    scheduled=False,
                )
                if previous_appointment:
                    previous_appointment = previous_appointment.earliest("counter")
                    previous_counter = previous_appointment.counter - 1
                appointment.counter = previous_appointment.counter
            else:
                previous_appointment = self.get_queryset().get(pk=previous_id)
                previous_counter = previous_appointment.counter
                appointment.counter = previous_appointment.counter + 1

            # Move the existing appointment forward by 1
            update_appointment(
                appointment, "active", increment=True, current_counter=previous_counter
            )

            appointment.status = "active"
            appointment.save()

            return Response({"detail": "Checked in successfully."})
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND
            )


class OrganizationListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
