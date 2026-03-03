import logging
from django.http import HttpResponse
from main.models import User
from rest_framework.response import Response
from rest_framework import status
from main.utils import getToken
from rest_framework.permissions import IsAuthenticated, AllowAny  # Add AllowAny here
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from main.decorators import view_set_error_handler
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken

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


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"status": "Failed", "message": "Email is required."}, status=400)

        # Check if the user exists
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return Response({"status": "Failed", "message": "User with this email does not exist."}, status=404)

        # Generate a random 6-digit OTP
        otp = get_random_string(length=6, allowed_chars="0123456789")
        cache_key = f"otp:{email}"
        cache.set(cache_key, otp, timeout=300)  # Store OTP in cache for 5 minutes

        # Send OTP via email
        try:
            send_mail(
                "Your OTP Code",
                f"Your OTP code is {otp}",
                "no-reply@sqip.com",
                [email],
                fail_silently=False,
            )
            return Response({"status": "Success", "message": "OTP sent successfully."}, status=200)
        except Exception as e:
            logger.error(f"Failed to send OTP: {str(e)}")
            return Response({"status": "Failed", "message": f"Failed to send OTP: {str(e)}"}, status=500)


class UserMeView(APIView):
    """Return current authenticated user info including groups."""

    permission_classes = (IsAuthenticated,)

    @view_set_error_handler
    def get(self, request):
        user = request.user
        groups = list(user.groups.values('id', 'name'))
        logger.info("User %d (%s) fetched /api/me/.", user.id, user.username)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'groups': groups,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"status": "Failed", "message": "Email and OTP are required."}, status=400)

        # Retrieve the OTP from the cache
        cache_key = f"otp:{email}"
        cached_otp = cache.get(cache_key)

        if cached_otp is None:
            return Response({"status": "Failed", "message": "OTP has expired or is invalid."}, status=400)

        if cached_otp == otp:
            # OTP is valid
            cache.delete(cache_key)  # Remove the OTP from the cache after successful verification

            # Retrieve the user
            try:
                user = get_user_model().objects.get(email=email)
            except get_user_model().DoesNotExist:
                return Response({"status": "Failed", "message": "User not found."}, status=404)

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response({
                "status": "Success",
                "message": "OTP verified successfully.",
                "refresh": str(refresh),
                "access": access_token,
                "id": user.id,
                "username": user.username
            }, status=200)
        else:
            return Response({"status": "Failed", "message": "Invalid OTP."}, status=400)
