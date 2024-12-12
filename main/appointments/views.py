from main.appointments.service import (
    handle_appointment_scheduling,
    move_appointment,
    activate_appointment,
)
from main.decorators import view_set_error_handler
from main.service import (
    get_scheduled_appointments_for_superuser,
    get_scheduled_appointments_for_user,
    get_unscheduled_appointments_for_superuser,
    get_unscheduled_appointments_for_user,
    get_user_appointments,
    set_appointment_status_and_update_counter,
)
from rest_framework.permissions import IsAuthenticated

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from main.models import Appointment
from main.appointments.serializers import (
    AppointmentIDValidatorSerializer,
    AppointmentListValidate,
    AppointmentSerializer,
    CreateAppointmentSerializer,
    MakeAppointmentSerializer,
    MoveAppointmentIDValidatorSerializer,
    ValidateAppointmentInput,
    AppointmentListQueryParamsSerializer,
    ValidateScheduledAppointmentInput,
)
from rest_framework.pagination import PageNumberPagination
import logging

logger = logging.getLogger('sqip')


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AppointmentListCreateView(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    pagination_class = StandardResultsSetPagination

    @view_set_error_handler
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

        query_params_serializer = AppointmentListValidate(
            data=request.query_params
        )

        query_params_serializer.is_valid(raise_exception=True)
        status_type = query_params_serializer.validated_data.get("type", "all")
        status = query_params_serializer.validated_data.get("status", "active")

        logger.info(
            "User %d (%s) requested appointments with type='%s' and status='%s'.",
            user.id, user.username, status_type, status
        )


        # Retrieve appointments based on the filter
        if status_type == "scheduled":
            appointments = get_user_appointments(user, is_scheduled=True, status=status)
        elif status_type == "unscheduled":
            appointments = get_user_appointments(
                user, is_scheduled=False, status=status
            )
        else:
            appointments = get_user_appointments(
                user, status=status
            )  # 'all' or invalid value

        # Paginate the queryset using StandardResultsSetPagination
        page = self.paginate_queryset(appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="scheduled")
    @view_set_error_handler
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
        
        logger.info(
            "User %d (%s) is listing scheduled appointments.",
            user.id, user.username
        )
        logger.debug(
            "Query parameters received: category_ids=%s, status=%s",
            category_ids, status
        )

        if user.is_superuser or user.is_staff:
            logger.info(
                "Superuser or staff user %d retrieving all scheduled appointments.",
                user.id
            )
            scheduled_appointments = get_scheduled_appointments_for_superuser(
                category_ids=category_ids, status=status
            )
        else:
            logger.info(
                "User %d with groups %s retrieving scheduled appointments.",
                user.id, user.groups.all()
            )
            scheduled_appointments = get_scheduled_appointments_for_user(
                user, category_ids=category_ids, status=status
            )

        page = self.paginate_queryset(scheduled_appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(scheduled_appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unscheduled")
    @view_set_error_handler
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
        
        logger.info(
            "User %d (%s) is listing unscheduled appointments.",
            user.id, user.username
        )
        logger.debug(
            "Query parameters received: category_ids=%s, status=%s",
            category_ids, status
        )

        if user.is_superuser or user.is_staff:
            logger.info(
                "Superuser or staff user %d retrieving all unscheduled appointments.",
                user.id
            )
            unscheduled_appointments = get_unscheduled_appointments_for_superuser(
                category_ids=category_ids, status=status
            )
        else:
            logger.info(
                "User %d with groups %s retrieving unscheduled appointments.",
                user.id, user.groups.all()
            )
            unscheduled_appointments = get_unscheduled_appointments_for_user(
                user, category_ids=category_ids, status=status
            )

        page = self.paginate_queryset(unscheduled_appointments)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AppointmentSerializer(unscheduled_appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="unschedule")
    @view_set_error_handler
    def unschedule(self, request):
        """Make appointment
        a user or Admin(behalf of any user) can make an appointment.

        payload:

        {
            "organization": 1,
            "category": 1,
            "user":2
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

        logger.debug(
            "Input data validated. Appointment data: %s",
            request.data
        )

        counter, error_message = handle_appointment_scheduling(
            input_serializer.validated_data
        )

        if error_message:
            logger.error(
                "Error scheduling appointment: %s",
                error_message
            )
            return Response(
                {"errors": {"appointment": [error_message]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set counter for new appointment
        serializer.validated_data["counter"] = counter
        serializer.validated_data["created_by"] = self.request.user
        logger.info(
            "Appointment created with counter %d.",
            counter
        )

        serializer.save(is_scheduled=False)
        logger.info(
            "Appointment successfully created for user %d.",
            self.request.user.id
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check-in")
    @view_set_error_handler
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
        success, message = set_appointment_status_and_update_counter(
            appointment_id, "checkin", self.request.user, ignore_status=True
        )

        if success:
            logger.info(
                "User %d successfully checked-in to appointment %s.",
                self.request.user.id, pk
            )
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            logger.error(
                "Failed to check-in to appointment %s: %s",
                pk, message
            )
            return Response({"errors": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cancel")
    @view_set_error_handler
    def cancel(self, request, pk=None):
        """Cancel to an appointment.

        Args:
            request: The request object containing appointment ID in query parameters.
            pk: Primary key of the appointment (not used in this method).

        Returns:
            Response: A response indicating the success or failure of the cancel operation.
        """

        # Validate appointment ID from query parameters
        user = self.request.user
        query_params_serializer = AppointmentIDValidatorSerializer(
            data={"appointment_id": pk},
            context={"request": request, "check_creator": True},
        )
        query_params_serializer.is_valid(raise_exception=True)
        appointment_id = query_params_serializer.validated_data["appointment_id"]

        logger.info(
            "User %d (%s) is attempting to cancel appointment %s.",
            user.id, user.username, pk
        )


        # Set appointment status to "cancel"
        success, message = set_appointment_status_and_update_counter(
            appointment_id, "cancel", self.request.user, ignore_status=True
        )

        if success:
            logger.info(
                "User %d successfully canceled appointment %s.",
                user.id, pk
            )
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            logger.error(
                "Failed to cancel appointment %s: %s",
                pk, message
            )
            return Response({"errors": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="activate")
    @view_set_error_handler
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
        user = self.request.user

        query_params_serializer = AppointmentIDValidatorSerializer(
            data={"appointment_id": pk}, context={"request": request}
        )
        query_params_serializer.is_valid(raise_exception=True)
        appointment_id = query_params_serializer.validated_data["appointment_id"]

        logger.info(
            "User %d (%s) is attempting to activate appointment %s.",
            user.id, user.username, pk
        )

        # Attempt to activate the appointment
        success, result = activate_appointment(appointment_id)

        if success:
            logger.info(
                "User %d successfully activated appointment %s.",
                user.id, pk
            )
            return Response(result, status=status.HTTP_200_OK)
        else:
            logger.error(
                "Failed to activate appointment %s: %s",
                pk, result
            )
            return Response({"errors": result}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="move")
    @view_set_error_handler
    def move(self, request, pk=None):
        """Move Unscheduled appointment up/down.

        If moving to first position `previous_appointment_id` will be null.
        Appointment will be moved behind the previous appointment.

        Args:
            pk (int): Appointmrnt ID.

        """

        # Validate appointment ID from query parameters
        user = self.request.user
        previous_appointment_id = request.data.get("previous_appointment_id")

        serializer = MoveAppointmentIDValidatorSerializer(
            data={
                "appointment_id": pk,
                "previous_appointment_id": previous_appointment_id,
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        logger.info(
            "User %d (%s) is attempting to move appointment %s.",
            user.id, user.username, pk
        )

        previous_appointment_id = serializer.validated_data["previous_appointment_id"]
        current_appointment_id = serializer.validated_data["appointment_id"]

        move_appointment(current_appointment_id, previous_appointment_id)
        
        previous_appointment_id = -1 if previous_appointment_id is None else previous_appointment_id
        logger.info(
            "Successfully moved appointment %d to position %d.",
            current_appointment_id, previous_appointment_id
        )

        return Response({}, status=status.HTTP_200_OK)


    @action(detail=False, methods=["post"], url_path="schedule")
    @view_set_error_handler
    def schedule(self, request):
        """
        POST /appointments/schedule/
        (EST)
        {
            "user": 1,
            "category": 7,
            "organization": 1,
            "scheduled_time": "2024-12-02T10:15"
        }

        """

        # Input validation
        input_serializer = ValidateScheduledAppointmentInput(
            data=request.data, context={"request": request}
        )
        input_serializer.is_valid(raise_exception=True)

        # Main serializer validation
        serializer = CreateAppointmentSerializer(
            data=request.data
        )

        logger.debug(
            "Input data validated. Appointment data: %s",
            request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.validated_data["scheduled_end_time"] = input_serializer.validated_data["scheduled_end_time"]

        # Save new appointment
        serializer.save(is_scheduled=True, status="active")
        logger.info(
            "Appointment successfully created for user %d.",
            self.request.user.id
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)