from rest_framework import serializers
from main.models import Organization

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'created_by', 'portfolio_site', 'display_picture', 
            'city', 'state', 'country', 'type', 'status', 'groups'
        ]
