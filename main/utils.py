from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
import json


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
