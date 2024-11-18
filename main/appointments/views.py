from main.appointments.service import handle_appointment_scheduling, move_appointment, activate_appointment
from main.service import (
    get_scheduled_appointments_for_superuser,
    get_scheduled_appointments_for_user,
    get_unscheduled_appointments_for_superuser,
    get_unscheduled_appointments_for_user,
    get_user_appointments,
    set_appointment_status,
)
from rest_framework.permissions import IsAuthenticated

from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from main.models import Appointment, Organization
from main.appointments.serializers import (
    AppointmentIDValidatorSerializer,
    AppointmentSerializer,
    MakeAppointmentSerializer,
    MoveAppointmentIDValidatorSerializer,
    ValidateAppointmentInput,
    AppointmentListQueryParamsSerializer,
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

        ?type=all (default)
        ?type=scheduled
        ?type=unscheduled

        ** Filter by status
            ?status=active (default)
            ?status=checkin
            ?status=inactive
        """
        user = self.request.user
        status_type = request.query_params.get("type", "all")
        status = request.query_params.get("status", "active")

        # Retrieve appointments based on the filter
        if status_type == "scheduled":
            appointments = get_user_appointments(user, is_scheduled=True, status=status)
        elif status_type == "unscheduled":
            appointments = get_user_appointments(user, is_scheduled=False, status=status)
        else:
            appointments = get_user_appointments(user, status=status)  # 'all' or invalid value

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

        ** Filter by status
        ?status=active (default)
        ?status=checkin
        ?status=inactive

        """
        user = self.request.user

        query_params_serializer = AppointmentListQueryParamsSerializer(
            data=request.query_params
        )
        query_params_serializer.is_valid(raise_exception=True)
        category_ids = query_params_serializer.validated_data.get("category_id", [])
        status = query_params_serializer.validated_data.get("status", "active")

        if user.is_superuser or user.is_staff:
            scheduled_appointments = get_scheduled_appointments_for_superuser(
                category_ids=category_ids, status=status
            )
        else:
            scheduled_appointments = get_scheduled_appointments_for_user(
                user, category_ids=category_ids, status=status
            )

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

        ** Filter by status
        ?status=active (default)
        ?status=checkin
        ?status=inactive
        """
        user = self.request.user

        query_params_serializer = AppointmentListQueryParamsSerializer(
            data=request.query_params
        )
        query_params_serializer.is_valid(raise_exception=True)
        category_ids = query_params_serializer.validated_data.get("category_id", [])
        status = query_params_serializer.validated_data.get("status", "active")

        if user.is_superuser or user.is_staff:
            unscheduled_appointments = get_unscheduled_appointments_for_superuser(
                category_ids=category_ids, status=status
            )
        else:
            unscheduled_appointments = get_unscheduled_appointments_for_user(
                user, category_ids=category_ids, status=status
            )

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
        input_serializer.is_valid(raise_exception=True)

        # Main serializer validation
        serializer = MakeAppointmentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

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
            serializer.validated_data["created_by"] = self.request.user
        else:
            Response({"errors": "Yet to Implement"}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        """Check-in to an appointment.

        Args:
            request: The request object containing appointment ID in query parameters.
            pk: Primary key of the appointment (not used in this method).

        Returns:
            Response: A response indicating the success or failure of the check-in operation.
        """

        # Validate appointment ID from query parameters
        query_params_serializer = AppointmentIDValidatorSerializer(
            data={"appointment_id": pk}, context={"request": request}
        )
        query_params_serializer.is_valid(raise_exception=True)
        appointment_id = query_params_serializer.validated_data["appointment_id"]

        # Set appointment status to "checkin"
        success, message = set_appointment_status(
            appointment_id, "checkin", self.request.user, ignore_status=True
        )

        if success:
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel to an appointment.

        Args:
            request: The request object containing appointment ID in query parameters.
            pk: Primary key of the appointment (not used in this method).

        Returns:
            Response: A response indicating the success or failure of the cancel operation.
        """

        # Validate appointment ID from query parameters
        query_params_serializer = AppointmentIDValidatorSerializer(
            data={"appointment_id": pk},
            context={"request": request, "check_creator": True},
        )
        query_params_serializer.is_valid(raise_exception=True)
        appointment_id = query_params_serializer.validated_data["appointment_id"]

        # Set appointment status to "cancel"
        success, message = set_appointment_status(
            appointment_id, "cancel", self.request.user, ignore_status=True
        )

        if success:
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": message}, status=status.HTTP_400_BAD_REQUEST)
        

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """
        Activate an appointment by setting its status to "active."

        This endpoint validates the appointment ID, activates the appointment if eligible,
        and returns the updated appointment details or an error message.

        Args:
            request: The request object containing appointment ID in query parameters.
            pk (str): The primary key of the appointment.

        Returns:
            Response: 
                - HTTP 200 with the updated appointment details if successful.
                - HTTP 400 with error messages if activation fails.
        """
        # Validate the appointment ID from the request parameters
        query_params_serializer = AppointmentIDValidatorSerializer(
            data={"appointment_id": pk}, context={"request": request}
        )
        query_params_serializer.is_valid(raise_exception=True)
        appointment_id = query_params_serializer.validated_data["appointment_id"]

        # Attempt to activate the appointment
        success, result = activate_appointment(appointment_id)

        if success:
            # Ensure result is a dictionary containing the updated appointment details
            return Response(result, status=status.HTTP_200_OK)
        else:
            # Return the error message if activation failed
            return Response({"errors": result}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        """Move Unscheduled appointment up/down.

        If moving to first position `previous_appointment_id` will be null.
        Appointment will be moved behind the previous appointment.

        Args:
            pk (int): Appointmrnt ID.

        """

        # Validate appointment ID from query parameters
        previous_appointment_id = request.data.get("previous_appointment_id")

        serializer = MoveAppointmentIDValidatorSerializer(
            data={
                "appointment_id": pk,
                "previous_appointment_id": previous_appointment_id,
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        previous_appointment_id = serializer.validated_data["previous_appointment_id"]
        current_appointment_id = serializer.validated_data["appointment_id"]

        move_appointment(current_appointment_id, previous_appointment_id)

        return Response({}, status=status.HTTP_200_OK)


