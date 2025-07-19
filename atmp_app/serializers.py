# /home/siisi/atmp/atmp_app/serializers.py

import bcrypt
from rest_framework import serializers
from django import forms 
from .models import (
    Audit, Contentieux, Document, DossierATMP, Action,
    AuditDecision, AuditStatus, ContentieuxStatus, JuridictionType,
    DocumentType, DossierStatus, UserRole
)
from users.models import CustomUser

# --- Serializers for nested JSONFields (if you want more structured validation/representation) ---
class AuditChecklistItemSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=255)
    answer = serializers.BooleanField(required=False, allow_null=True)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    documentRequired = serializers.BooleanField(required=False)
    documentReceived = serializers.BooleanField(required=False)

class JuridictionStepSerializer(serializers.Serializer):
    juridiction = serializers.ChoiceField(choices=JuridictionType.choices())
    submittedAt = serializers.DateTimeField()
    decision = serializers.CharField(required=False, allow_blank=True)
    decisionAt = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

class TemoinSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=255)
    coordonnees = serializers.CharField(max_length=255, required=False, allow_blank=True)

class TiersSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=255, required=False, allow_blank=True)
    adresse = serializers.CharField(max_length=255, required=False, allow_blank=True)
    assurance = serializers.CharField(max_length=255, required=False, allow_blank=True)
    immatriculation = serializers.CharField(max_length=255, required=False, allow_blank=True)

# --- Main Model Serializers ---
class DocumentSerializer(serializers.ModelSerializer):
    # For ForeignKey fields, use PrimaryKeyRelatedField to represent by ID
    contentieux = serializers.PrimaryKeyRelatedField(queryset=Contentieux.objects.all())
    uploaded_by = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    
    # For FileField, Django REST Framework handles file uploads automatically
    # The 'file' field will be handled by MultiPartParser in views

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class ContentieuxSerializer(serializers.ModelSerializer):
    dossier_atmp = serializers.PrimaryKeyRelatedField(queryset=DossierATMP.objects.all())
    
    # JSONField will be serialized as Python dicts/lists
    subject = serializers.JSONField()
    juridiction_steps = serializers.JSONField()

    # For ManyToManyField, use PrimaryKeyRelatedField to represent by IDs
    documents = serializers.PrimaryKeyRelatedField(many=True, queryset=Document.objects.all(), required=False)
    actions = serializers.PrimaryKeyRelatedField(many=True, queryset=Action.objects.all(), required=False)

    class Meta:
        model = Contentieux
        fields = '__all__'
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']

        
class DossierATMPSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        style={'input_type': 'select'}
    )
    
    # JSON fields with proper widget definitions
    entreprise = serializers.JSONField(
        style={
            'base_template': 'textarea.html',
            'rows': 10,
            'placeholder': '{"nom": "", "siret": "", "adresse": ""}'
        }
    )
    
    documents = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Document.objects.all(),
        required=False,
        style={
            'base_template': 'select_multiple.html',
            'input_type': 'select'
        }
    )
    
    class Meta:
        model = DossierATMP
        fields = '__all__'
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']


class AuditSerializer(serializers.ModelSerializer):
    dossier_atmp = serializers.PrimaryKeyRelatedField(queryset=DossierATMP.objects.all())
    auditor = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    
    # JSONField for checklist
    checklist = serializers.JSONField()

    class Meta:
        model = Audit
        fields = '__all__'
        read_only_fields = ['id', 'started_at', 'completed_at', 'created_at', 'updated_at']

class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']



#
#from rest_framework import serializers
#from .models import ATMPIncident, ATMPDocument
#
#
#class ATMPDocumentSerializer(serializers.ModelSerializer):
#    uploaded_by_email = serializers.SerializerMethodField()
#    
#    class Meta:
#        model = ATMPDocument
#        fields = ['id', 'file', 'description', 'uploaded_at', 'uploaded_by_email']
#        read_only_fields = ['uploaded_at', 'uploaded_by_email']
#    
#    def get_uploaded_by_email(self, obj):
#        return obj.uploaded_by.email
#
#
#class ATMPIncidentSerializer(serializers.ModelSerializer):
#    documents = ATMPDocumentSerializer(many=True, read_only=True)
#    provider_email = serializers.SerializerMethodField()
#    safety_manager_email = serializers.SerializerMethodField()
#    
#    class Meta:
#        model = ATMPIncident
#        fields = [
#            'id', 'provider', 'provider_email', 'safety_manager', 'safety_manager_email',
#            'title', 'description', 'date_of_incident', 'location',
#            'status', 'created_at', 'documents'
#        ]
#        read_only_fields = ['created_at', 'provider_email', 'safety_manager_email']
#    
#    def get_provider_email(self, obj):
#        return obj.provider.email
#    
#    def get_safety_manager_email(self, obj):
#        return obj.safety_manager.email
#