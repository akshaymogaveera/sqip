# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client
from django.contrib.auth.models import Group

# Set environment variables for your credentials
# Read more at http://twil.io/secure
account_sid = "123"
auth_token = "abc"
verify_sid = "edf"
client = Client(account_sid, auth_token)

def twilioSendSms(phone_number):
    try:
        verification = client.verify.v2.services(verify_sid) \
        .verifications \
        .create(to=phone_number, channel="sms")
    except Exception:
        return False
    return verification

def twilioVerifySms(otp_code, phone_number):
    try:
        verification_check = client.verify.v2.services(verify_sid) \
        .verification_checks \
        .create(to=phone_number, code=otp_code)
    except Exception:
        return False
    return verification_check

def check_user_in_group(user, group):
    try:
        return user.groups.filter(id=group.id).exists()
    except Group.DoesNotExist:
        return False

def check_if_user_is_authorized(user, appointment, group):
    if check_user_in_group(user, group):
        return True
    if appointment.user == user:
        return True
    return False
