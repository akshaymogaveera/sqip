from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.timezone import now
import pytz


def authenticateUser(username, password):
    if username is not None and password is not None:
        print("validateUser")
        print(username)
        print(password)
        user = authenticate(username=username, password=password)
        return user
    else:
        return None

def getToken(user):
    if user:
        if user.is_active:
            refresh = RefreshToken.for_user(user)
            return str(refresh), str(refresh.access_token)
        else:
            return None, None
        

def convert_time_to_utc(scheduled_time, category_timezone_str):
    """
    Converts the time (ignoring any timezone info from input) to UTC.
    
    Args:
        scheduled_time (datetime): The scheduled time in naive or timezone-aware format.
        category_timezone_str (str): The timezone string associated with the category (e.g., 'US/Eastern').

    Returns:
        datetime: The converted time in UTC.
    """
    # Step 1: Get the timezone for the category
    category_timezone = pytz.timezone(category_timezone_str)

    # Step 2: If the datetime is timezone-aware, remove the timezone info first
    if scheduled_time.tzinfo is not None:
        scheduled_time = scheduled_time.replace(tzinfo=None)  # Strip timezone info

    # Step 3: Localize the naive datetime to the category's timezone
    scheduled_time = category_timezone.localize(scheduled_time)  # Localize to the category's timezone

    # Step 4: Convert to UTC
    utc_time = scheduled_time.astimezone(pytz.utc)

    return utc_time


def convert_utc_to_category_timezone(utc_time, category_timezone_str):
    """
    Converts a UTC time to the specified category's timezone.

    Args:
        utc_time (datetime): The time in UTC.
        category_timezone_str (str): The timezone string associated with the category (e.g., 'US/Eastern').

    Returns:
        datetime: The converted time in the category's timezone.
    """
    # Step 1: Get the timezone for the category
    category_timezone = pytz.timezone(category_timezone_str)

    # Step 2: Convert the UTC time to the category's timezone
    category_time = utc_time.astimezone(category_timezone)

    return category_time
