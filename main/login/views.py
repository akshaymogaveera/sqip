import logging
from django.http import HttpResponse
from main.models import User
from rest_framework.response import Response
import jsonschema
from rest_framework import status
from main.utils import getToken
from main.verification.utils import twilioSendSms, twilioVerifySms
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from main.decorators import view_set_error_handler

logger = logging.getLogger('sqip')

def index(request):
    return HttpResponse('Hello, welcome to SQIP!.')

class ValidateToken(APIView):
    """Endpoint for validating and refreshing a user’s authentication token."""
    
    permission_classes = (IsAuthenticated,)

    @view_set_error_handler
    def get(self, request):
        user = request.user
        if user.is_authenticated:
            refresh_token, access_token = getToken(user)
            logger.info("User %d (%s) validated their token successfully.", user.id, user.username)
            return Response({
                'status': 'Success',
                'refresh': refresh_token,
                'access': access_token,
                'id': user.id
            }, status=status.HTTP_200_OK)

        logger.warning("Authentication failed for user %d (%s).", user.id, user.username)
        return Response({'status': 'Failed', 'message': "Authentication Failed"}, status=status.HTTP_401_UNAUTHORIZED)


class AuthenticateUser(APIView):
    """Endpoint for authenticating a user and generating tokens."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.access_token = None
        self.refresh_token = None

    def post(self, request):
        """Generate auth token

        Args:
            request (_type_): _description_

        Returns:
            JSON: Auth Info
        """
        username = request.data.get('username')
        if not username:
            logger.error("Username is required for authentication.")
            return Response({'status': 'Failed', 'message': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.user = get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            logger.error("User %s not found during authentication.", username)
            return Response({'status': 'Failed', 'message': "User not found"}, status=status.HTTP_404_NOT_FOUND)

        self.refresh_token, self.access_token = getToken(self.user)
        logger.info("User %d (%s) authenticated successfully.", self.user.id, self.user.username)
        return Response({
            'status': 'Success',
            'refresh': self.refresh_token,
            'access': self.access_token,
            'id': self.user.id,
            'username': self.user.username
        }, status=status.HTTP_200_OK)



class sendSms(APIView):
    def post(self, request):
        phone_number = str(request.POST['phone'])

        response = twilioSendSms(phone_number)
        print("status: ", response.status)
        if response:
            return Response({'detail': 'OTP sent sucessfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'errors': {"error": "Failed"}}, status=status.HTTP_400_BAD_REQUEST)


class verifySms(APIView):
    def post(self, request):
        phone_number = str(request.POST['phone'])
        otp = str(request.POST['otp'])
        first_name = str(request.POST['first_name'])
        last_name = str(request.POST['last_name'])
        response = twilioVerifySms(otp, "+919167119168")

        if isinstance(response, bool):
            return Response({'errors': {"error": "Please request a new otp"}}, status=status.HTTP_400_BAD_REQUEST)

        print("status: ", response.status)
        if response.status == "approved":
            # Check if user with the given phone number already exists
            user_exists = User.objects.filter(username=phone_number).exists()

            if user_exists:
                user = User.objects.get(username=phone_number)
            else:
                # Create a new user
                user = User(username=phone_number, first_name=first_name, last_name=last_name)
                user.save()

            refresh, access_token = getToken(user)

            return Response({'refresh': refresh, 'access': access_token, 'id': user.id,
                                    'userName': user.username}, status=status.HTTP_200_OK)
        else:
            return Response({'errors': {"error": "Failed"}}, status=status.HTTP_400_BAD_REQUEST)
