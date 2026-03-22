from rest_framework import serializers
from main.models import Organization
import phonenumbers as pn

class OrganizationSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()
    display_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'created_by', 'portfolio_site', 'display_picture',
            'display_picture_base64', 'display_picture_url',
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

    def get_display_picture_url(self, obj):
        """Return the best available picture: base64 data-URL first, then a filesystem URL, else None."""
        if obj.display_picture_base64:
            return obj.display_picture_base64
        if obj.display_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.display_picture.url)
            return obj.display_picture.url
        return None
