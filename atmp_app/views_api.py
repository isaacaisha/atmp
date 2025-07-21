# /home/siisi/atmp/atmp_app/views_api.py

import logging
import os 
import mimetypes 
from rest_framework import generics, status, viewsets, mixins
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser 
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404 
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, ValidationError 
from django.db.models import Count 


from .models import (
    Audit, Contentieux, Document, DossierATMP,
    AuditDecision, AuditStatus, DossierStatus
)
from .serializers import (
    DossierCreateSerializer,
    AuditSerializer, AuditUpdateSerializer,
    ContentieuxCreateSerializer, ContentieuxSerializer, ContentieuxStatus,
    DocumentSerializer, DossierATMPSerializer
)
from .services import ContentieuxService
from .permissions import IsSafetyManager, IsJurist, IsSuperuserOrEmployee, IsRH, IsQSE, IsDirection 
from users.models import UserRole 

logger = logging.getLogger(__name__)


# --- Custom API Views (for browsable API root) ---
class CustomAPIRootView(APIRootView):
    def get(self, request, *args, **kwargs):
        return Response({
            'authentication': {
                'register': reverse('atmp_app:auth-register', request=request),
                'login': reverse('atmp_app:auth-login', request=request),
                'profile': reverse('atmp_app:auth-profile', request=request),
                'logout': reverse('atmp_app:auth-logout', request=request),
            },
            'resources': {
                'dossiers': reverse('atmp_app:dossier-list', request=request),
                'contentieux': reverse('atmp_app:contentieux-list', request=request),
                'audits': reverse('atmp_app:audit-list', request=request),
                'documents': reverse('atmp_app:document-list', request=request),
            },
            'actions': {
                'dashboard_juridique': reverse('atmp_app:jurist_dashboard_data', request=request),
                'dashboard_rh': reverse('atmp_app:rh_dashboard_data', request=request),
                'dashboard_qse': reverse('atmp_app:qse_dashboard_data', request=request),
                'dashboard_direction': reverse('atmp_app:direction_dashboard_data', request=request),
            },
            'extras': {
                'superuser admin panel': request.build_absolute_uri('/admin/'),
                'back to dashboard': reverse('atmp_app:dashboard', request=request),
                'github_repo': 'https://github.com/isaacaisha/atmp'
            },
        })

class CustomDefaultRouter(DefaultRouter):
    APIRootView = CustomAPIRootView


# --- Dossier Views ---
class DossierViewSet(viewsets.ModelViewSet):
    queryset = DossierATMP.objects.select_related(
        'safety_manager', 'created_by', 'contentieux', 'audit' 
    ).prefetch_related(
        'documents', 'temoin_set', 'contentieux__documents', 'contentieux__juridiction_steps_set' 
    ).order_by('-created_at')
    
    serializer_class = DossierATMPSerializer
    permission_classes = [IsAuthenticated, IsSuperuserOrEmployee]

    def get_serializer_class(self):
        if self.action == 'create':
            return DossierCreateSerializer
        return DossierATMPSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset() 
        elif user.role == UserRole.EMPLOYEE: 
            return super().get_queryset().filter(created_by=user)
        elif user.role == UserRole.SAFETY_MANAGER: 
            return super().get_queryset().filter(safety_manager=user)
        return DossierATMP.objects.none() 

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# --- Contentieux Views ---
class ContentieuxViewSet(viewsets.ModelViewSet):
    queryset = Contentieux.objects.all().order_by('-created_at')
    serializer_class = ContentieuxSerializer
    permission_classes = [IsAuthenticated, IsJurist] 

    def get_serializer_class(self):
        if self.action == 'create':
            return ContentieuxCreateSerializer 
        return ContentieuxSerializer

    def perform_create(self, serializer):
        serializer.save(status=ContentieuxStatus.DRAFT)


# --- Audit Views ---
class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.all().order_by('-created_at')
    serializer_class = AuditSerializer
    permission_classes = [IsAuthenticated, IsSafetyManager] 

    @action(detail=False, methods=['get'], url_path='by-dossier/(?P<dossier_id>[^/.]+)')
    def by_dossier(self, request, dossier_id=None):
        audit = get_object_or_404(Audit, dossier_atmp_id=dossier_id)
        serializer = self.get_serializer(audit)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        audit = self.get_object()
        
        serializer = AuditUpdateSerializer(audit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        decision_value = serializer.validated_data.get('decision')
        comments = serializer.validated_data.get('comments', audit.comments)
        
        if not decision_value:
            return Response(
                {"message": "Decision is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            decision = AuditDecision(decision_value)
        except ValueError:
            return Response(
                {"message": "Invalid decision"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if audit.status == AuditStatus.COMPLETED:
            return Response(
                {"message": "Audit already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        audit.status = AuditStatus.COMPLETED.value
        audit.decision = decision.value
        audit.comments = comments 
        audit.completed_at = timezone.now()
        audit.save()

        dossier = audit.dossier_atmp
        
        new_contentieux_data = None
        if decision == AuditDecision.CONTEST:
            dossier.status = DossierStatus.CONTESTATION_RECOMMANDEE.value
            new_contentieux = ContentieuxService.create_from_audit(audit, dossier)
            dossier.status = DossierStatus.TRANSFORME_EN_CONTENTIEUX.value 
            new_contentieux_data = ContentieuxSerializer(new_contentieux).data
        else:
            dossier.status = DossierStatus.CLOTURE_SANS_SUITE.value 
        
        dossier.save() 

        response_data = {
            "message": "Audit finalized successfully",
            "audit": AuditSerializer(audit).data
        }
        if new_contentieux_data:
            response_data["message"] = "Audit finalized and litigation created"
            response_data["contentieux"] = new_contentieux_data

        return Response(response_data, status=status.HTTP_200_OK)


# --- Document Views ---
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated] 
    parser_classes = [MultiPartParser, FormParser] 

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        try:
            if not document.file or not document.file.name:
                return Response({"message": "File not found for this document."}, status=status.HTTP_404_NOT_FOUND)
            
            file_path = document.file.path
            if not os.path.exists(file_path):
                logger.error(f"File not found on disk for Document ID {document.pk} at path {file_path}")
                return Response({"message": "File not found on server storage."}, status=status.HTTP_404_NOT_FOUND)

            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = document.mime_type or 'application/octet-stream' 

            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.original_name
            )
            response['Content-Type'] = mime_type
            return response
        except FileNotFoundError:
            logger.error(f"FileNotFoundError for Document ID {document.pk} at path {document.file.path}")
            return Response(
                {"message": "File not found on server"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error downloading document {document.pk}: {e}", exc_info=True)
            return Response(
                {"message": f"Error downloading document: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# --- Dashboard API Views (function-based for specific dashboard data) ---

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsJurist]) 
def get_jurist_dashboard_data(request):
    """
    GET /atmp/api/dashboard/juridique/
    """
    total_contentieux = Contentieux.objects.count()
    pending_contentieux = Contentieux.objects.filter(status=ContentieuxStatus.EN_COURS).count()
    contentieux_by_status = Contentieux.objects.values('status').annotate(count=Count('id')).order_by('status')
    recent_contentieux = Contentieux.objects.order_by('-created_at')[:5].values('id', 'reference', 'status', 'created_at')

    return Response(
        {
            "totalContentieux": total_contentieux,
            "pendingContentieux": pending_contentieux,
            "contentieuxByStatus": list(contentieux_by_status),
            "recentContentieux": list(recent_contentieux),
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsRH]) 
def get_rh_dashboard_data(request):
    """
    GET /atmp/api/dashboard/rh/
    """
    total_dossiers = DossierATMP.objects.count()
    incidents_a_analyser = DossierATMP.objects.filter(status=DossierStatus.A_ANALYSER).count()
    incidents_by_status = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
    
    incidents_created_by_employee = DossierATMP.objects.filter(created_by__role=UserRole.EMPLOYEE).count()

    return Response(
        {
            "totalDossiers": total_dossiers,
            "incidentsAAnalyser": incidents_a_analyser,
            "incidentsByStatus": list(incidents_by_status),
            "incidentsCreatedByEmployee": incidents_created_by_employee,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsQSE]) 
def get_qse_dashboard_data(request):
    """
    GET /atmp/api/dashboard/qse/
    """
    total_dossiers = DossierATMP.objects.count()
    audits_completed = Audit.objects.filter(status=AuditStatus.COMPLETED).count()
    audits_in_progress = Audit.objects.filter(status=AuditStatus.IN_PROGRESS).count()
    dossiers_contested_recommended = DossierATMP.objects.filter(audit__decision=AuditDecision.CONTEST).count()

    return Response(
        {
            "totalDossiers": total_dossiers,
            "auditsCompleted": audits_completed,
            "auditsInProgress": audits_in_progress,
            "dossiersContestedRecommended": dossiers_contested_recommended,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDirection]) 
def get_direction_dashboard_data(request):
    """
    GET /atmp/api/dashboard/direction/
    """
    try:
        open_dossiers = DossierATMP.objects.exclude(
            status=DossierStatus.CLOTURE_SANS_SUITE.value
        ).count()
        total_dossiers = DossierATMP.objects.count()
        estimated_risk_per_case = 5000
        total_risk_value = open_dossiers * estimated_risk_per_case

        contentieux_counts = Contentieux.objects.values('status').annotate(count=Count('id'))
        audit_decisions = Audit.objects.values('decision').annotate(count=Count('id'))
        
        case_type_distribution = [] 

        return Response({
            "stats": {
                "openDossiers": open_dossiers,
                "totalDossiers": total_dossiers,
                "totalRiskValue": total_risk_value,
                "contentieuxCounts": list(contentieux_counts),
                "auditDecisions": list(audit_decisions),
            },
            "caseTypeDistribution": case_type_distribution,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données du tableau de bord Direction: {e}", exc_info=True)
        return Response(
            {"message": "Erreur lors de la récupération des données du tableau de bord Direction."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
