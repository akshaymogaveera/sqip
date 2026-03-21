from rest_framework import serializers
from main.models import Organization
import phonenumbers as pn

class OrganizationSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'created_by', 'portfolio_site', 'display_picture',
            'city', 'state', 'country',
            'address_line1', 'address_line2', 'pincode', 'phone_number',
            'type', 'status', 'groups',
        ]

    def get_phone_number(self, obj):
        if obj.phone_number:
            try:
                return pn.format_number(obj.phone_number, pn.PhoneNumberFormat.E164)
            except Exception:
                return str(obj.phone_number)
        return None
