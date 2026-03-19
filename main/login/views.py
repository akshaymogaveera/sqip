import logging
from django.http import HttpResponse
from main.models import User, Profile
from rest_framework.response import Response
from rest_framework import status
from main.utils import getToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from main.decorators import view_set_error_handler
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
import phonenumbers

logger = logging.getLogger('sqip')


def _normalize_phone(raw: str):
    """Parse raw string and return E.164 form, or None on failure."""
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw.strip(), None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    return None


def index(request):
    return HttpResponse('Hello, welcome to SQIP!.')


class ValidateToken(APIView):
    """Endpoint for validating and refreshing a user's authentication token."""

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
    """
    Authenticate with phone number OR username (no password — token-based, admin-style flow).
    POST /api/auth/
    { "identifier": "+911234567890" }   or   { "identifier": "admin_username" }
    Also accepts legacy { "username": "..." } key for backwards compat.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        identifier = (
            request.data.get('identifier')
            or request.data.get('username')
            or request.data.get('phone')
            or ''
        ).strip()

        if not identifier:
            return Response(
                {'status': 'Failed', 'message': 'Phone number or username is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        user = None

        # Try phone-number lookup first
        normalized = _normalize_phone(identifier)
        if normalized:
            try:
                profile = Profile.objects.select_related('user').get(phone_number=normalized)
                user = profile.user
            except Profile.DoesNotExist:
                pass

        # Fall back to username
        if user is None:
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                pass

        if user is None:
            logger.error("No user found for identifier '%s'.", identifier)
            return Response({'status': 'Failed', 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        refresh_token, access_token = getToken(user)
        logger.info("User %d (%s) authenticated successfully.", user.id, user.username)
        return Response({
            'status': 'Success',
            'refresh': refresh_token,
            'access': access_token,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=status.HTTP_200_OK)


class RegisterUser(APIView):
    """
    Register a new regular user with phone as primary identifier.
    POST /api/register/
    {
        "first_name": "Palakh",
        "last_name": "Kanwar",           // optional
        "phone": "+911234567890",
        "email": "optional@example.com"  // optional
    }
    Returns JWT tokens on success (auto-login after registration).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        first_name = (request.data.get('first_name') or '').strip()
        last_name = (request.data.get('last_name') or '').strip()
        phone_raw = (request.data.get('phone') or '').strip()
        email = (request.data.get('email') or '').strip()

        errors = {}
        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not phone_raw:
            errors['phone'] = 'Phone number is required.'
        if errors:
            return Response({'status': 'Failed', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        normalized_phone = _normalize_phone(phone_raw)
        if not normalized_phone:
            return Response(
                {'status': 'Failed', 'errors': {'phone': 'Invalid phone number. Include country code (e.g. +91...).'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()

        if Profile.objects.filter(phone_number=normalized_phone).exists():
            return Response(
                {'status': 'Failed', 'errors': {'phone': 'An account with this phone number already exists.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email and User.objects.filter(email=email).exists():
            return Response(
                {'status': 'Failed', 'errors': {'email': 'An account with this email already exists.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction
        try:
            with transaction.atomic():
                base = 'user' + normalized_phone[-7:].replace('+', '')
                username = base
                suffix = 0
                while User.objects.filter(username=username).exists():
                    suffix += 1
                    username = f'{base}{suffix}'

                user = User.objects.create_user(
                    username=username,
                    email=email or '',
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_unusable_password()
                user.save()

                Profile.objects.create(user=user, phone_number=normalized_phone)
        except Exception as e:
            logger.error("Registration failed: %s", str(e))
            return Response({'status': 'Failed', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        refresh_token, access_token = getToken(user)
        logger.info("New user %d (%s) registered via phone %s.", user.id, user.username, normalized_phone)
        return Response({
            'status': 'Success',
            'refresh': refresh_token,
            'access': access_token,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=status.HTTP_201_CREATED)


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"status": "Failed", "message": "Email is required."}, status=400)

        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return Response({"status": "Failed", "message": "User with this email does not exist."}, status=404)

        otp = get_random_string(length=6, allowed_chars="0123456789")
        cache_key = f"otp:{email}"
        cache.set(cache_key, otp, timeout=300)

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
        phone = None
        try:
            phone = str(user.profile.phone_number) if user.profile.phone_number else None
        except Exception:
            pass
        # Include org-admin flags and org_access list when available
        is_org_admin = False
        org_access = []
        try:
            is_org_admin = bool(user.profile.is_org_admin)
            org_access = list(user.profile.org_access.values_list('id', flat=True))
        except Exception:
            pass

        return Response({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': phone,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_org_admin': is_org_admin,
            'org_access': org_access,
            'groups': groups,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"status": "Failed", "message": "Email and OTP are required."}, status=400)

        cache_key = f"otp:{email}"
        cached_otp = cache.get(cache_key)

        if cached_otp is None:
            return Response({"status": "Failed", "message": "OTP has expired or is invalid."}, status=400)

        if cached_otp == otp:
            cache.delete(cache_key)
            try:
                user = get_user_model().objects.get(email=email)
            except get_user_model().DoesNotExist:
                return Response({"status": "Failed", "message": "User not found."}, status=404)

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response({
                "status": "Success",
                "message": "OTP verified successfully.",
                "refresh": str(refresh),
                "access": access_token,
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }, status=200)
        else:
            return Response({"status": "Failed", "message": "Invalid OTP."}, status=400)
