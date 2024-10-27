from django.shortcuts import render
from django.http import HttpResponse
from main.models import User
from rest_framework.response import Response
import jsonschema

from rest_framework import status
from django.contrib.auth import login, logout
from main.utils import authenticateUser, getToken
from main.verification.utils import twilioSendSms, twilioVerifySms
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import JsonResponse
from django.contrib.auth import get_user_model

def index(request):
    return HttpResponse('Hello, welcome to the index page.')


class ValidateToken(APIView):
    """Endpoint for validating and refreshing a user’s authentication token."""
    
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.is_authenticated:
            refresh_token, access_token = getToken(user)  # Assume `getToken` is defined elsewhere
            return JsonResponse({
                'status': 'Success',
                'refresh': refresh_token,
                'access': access_token,
                'id': user.id
            })
        
        return JsonResponse({'status': 'Failed', 'message': "Authentication Failed"}, status=401)


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
            return JsonResponse({'status': 'Failed', 'message': 'Username is required'}, status=400)

        try:
            self.user = get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return JsonResponse({'status': 'Failed', 'message': "User not found"}, status=404)

        self.refresh_token, self.access_token = getToken(self.user)  # Assume `getToken` is defined elsewhere

        return JsonResponse({
            'status': 'Success',
            'refresh': self.refresh_token,
            'access': self.access_token,
            'id': self.user.id,
            'username': self.user.username
        })



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
