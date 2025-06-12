# /home/siisi/atmp/atmp_app/serializers.py

from rest_framework import serializers
from .models import ATMPIncident, ATMPDocument


class ATMPDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.SerializerMethodField()
    
    class Meta:
        model = ATMPDocument
        fields = ['id', 'file', 'description', 'uploaded_at', 'uploaded_by_email']
        read_only_fields = ['uploaded_at', 'uploaded_by_email']
    
    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email


class ATMPIncidentSerializer(serializers.ModelSerializer):
    documents = ATMPDocumentSerializer(many=True, read_only=True)
    provider_email = serializers.SerializerMethodField()
    safety_manager_email = serializers.SerializerMethodField()
    
    class Meta:
        model = ATMPIncident
        fields = [
            'id', 'provider', 'provider_email', 'safety_manager', 'safety_manager_email',
            'title', 'description', 'date_of_incident', 'location',
            'status', 'created_at', 'documents'
        ]
        read_only_fields = ['created_at', 'provider_email', 'safety_manager_email']
    
    def get_provider_email(self, obj):
        return obj.provider.email
    
    def get_safety_manager_email(self, obj):
        return obj.safety_manager.email
