# /home/siisi/atmp/atmp_app/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model # <--- Get Django's active User model
from .models import (
    DossierATMP, Contentieux, Audit, Document, 
    JuridictionStep, Temoin, Tiers, Action, UploadedFile,
    AuditDecision, AuditStatus, ContentieuxStatus,
    JuridictionType, DocumentType, DossierStatus, AuditChecklistItem
)
from users.models import CustomUser

User = get_user_model() # Get the actual User model defined in settings.AUTH_USER_MODEL


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'role']


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = CustomUserSerializer(read_only=True)
    document_type_display = serializers.CharField(
        source='get_document_type_display', 
        read_only=True
    )

    class Meta:
        model = Document
        fields = [
            'id', 'contentieux', 'uploaded_by', 'document_type', 
            'document_type_display', 'original_name', 'file', 
            'mime_type', 'size', 'created_at'
        ]
        read_only_fields = ['mime_type', 'size', 'created_at', 'uploaded_by']
        extra_kwargs = {
            'file': {'write_only': True}
        }

    def create(self, validated_data):
        # Automatically set uploaded_by to current user
        validated_data['uploaded_by'] = self.context['request'].user
        
        # Set file properties
        file = validated_data.get('file')
        if file:
            validated_data['mime_type'] = file.content_type
            validated_data['size'] = file.size
            validated_data['original_name'] = file.name
            
        return super().create(validated_data)


class JuridictionStepSerializer(serializers.ModelSerializer):
    juridiction_display = serializers.CharField(
        source='get_juridiction_display', 
        read_only=True
    )
    decision_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JuridictionStep
        fields = [
            'id', 'contentieux', 'juridiction', 'juridiction_display',
            'submitted_at', 'decision', 'decision_display',
            'decision_at', 'notes'
        ]

    def get_decision_display(self, obj):
        if obj.decision:
            return dict(JuridictionStep._meta.get_field('decision').choices)[obj.decision]
        return None


class ContentieuxSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    documents = DocumentSerializer(many=True, read_only=True)
    juridiction_steps = JuridictionStepSerializer(many=True, read_only=True)
    actions = ActionSerializer(many=True, read_only=True)

    class Meta:
        model = Contentieux
        fields = [
            'id', 'dossier_atmp', 'reference', 'subject', 'status', 'status_display',
            'documents', 'juridiction_steps', 'actions', 'created_at'
        ]
        read_only_fields = ['reference', 'created_at']


class ContentieuxCreateSerializer(ContentieuxSerializer):
    dossier_atmp = serializers.PrimaryKeyRelatedField(
        queryset=DossierATMP.objects.all()
    )


class AuditSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    decision_display = serializers.CharField(
        source='get_decision_display', 
        read_only=True
    )
    auditor = CustomUserSerializer(read_only=True)

    class Meta:
        model = Audit
        fields = [
            'id', 'dossier_atmp', 'auditor', 'status', 'status_display',
            'decision', 'decision_display', 'comments', 'started_at',
            'completed_at', 'created_at'
        ]
        read_only_fields = ['started_at', 'completed_at', 'created_at']


class AuditUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = ['status', 'decision', 'comments']


class AuditChecklistItemSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=255)
    answer = serializers.BooleanField(required=False, allow_null=True)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    documentRequired = serializers.BooleanField(required=False)
    documentReceived = serializers.BooleanField(required=False)


class TemoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temoin
        fields = ['id', 'nom', 'coordonnees']


class TiersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tiers
        fields = ['id', 'nom', 'adresse', 'assurance', 'immatriculation']


# --- UploadedFile Serializer (Now a ModelSerializer) ---
class UploadedFileSerializer(serializers.ModelSerializer):
    # Write-only input
    contentieux = serializers.PrimaryKeyRelatedField(queryset=Contentieux.objects.all(), write_only=True)
    uploaded_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)

    # Read-only output
    contentieux_id = serializers.PrimaryKeyRelatedField(read_only=True, source='contentieux')
    uploaded_by_id = serializers.PrimaryKeyRelatedField(read_only=True, source='uploaded_by')

    class Meta:
        model = UploadedFile
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at',
            'filename', 'path', 'size',
            'contentieux_id', 'uploaded_by_id',
        )

    def create(self, validated_data):
        """
        Create UploadedFile instance. If you need to programmatically
        assign related fields like contentieux or uploaded_by,
        you can do it here.
        """
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Optional: update logic.
        """
        return super().update(instance, validated_data)


class DossierATMPSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    safety_manager = CustomUserSerializer(read_only=True)
    created_by = CustomUserSerializer(read_only=True)
    contentieux = ContentieuxSerializer(read_only=True)
    audit = AuditSerializer(read_only=True)
    temoins = TemoinSerializer(many=True, read_only=True)
    tiers = TiersSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = DossierATMP
        fields = [
            'id', 'reference', 'safety_manager', 'title', 'description',
            'date_of_incident', 'location', 'status', 'status_display',
            'created_by', 'entreprise', 'salarie', 'accident',
            'service_sante', 'documents', 'contentieux', 'audit',
            'temoins', 'tiers', 'created_at'
        ]
        read_only_fields = ['reference', 'created_at', 'contentieux', 'audit']

    def validate_entreprise(self, value):
        required_fields = ['name', 'siret', 'address']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field in entreprise: {field}")
        return value

    def validate_salarie(self, value):
        required_fields = ['first_name', 'last_name', 'social_security_number']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field in salarie: {field}")
        return value

    def validate_accident(self, value):
        required_fields = ['date', 'time', 'description']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field in accident: {field}")
        return value

# Special serializers for write operations
class DossierCreateSerializer(DossierATMPSerializer):
    safety_manager = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='SAFETY_MANAGER')
    )
    
    class Meta:
        model = DossierATMP
        fields = [
            'safety_manager', 'title', 'description',
            'date_of_incident', 'location', 'entreprise',
            'salarie', 'accident', 'service_sante'
        ]
