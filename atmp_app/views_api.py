# /home/siisi/atmp/atmp_app/views_api.py

import logging
import os
import mimetypes
from rest_framework import generics, status, viewsets, mixins
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse # Import reverse
from rest_framework.routers import DefaultRouter, APIRootView # Import APIRootView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count


from .models import (
    Audit, Contentieux, ContentieuxStatus, Document, DossierATMP,
    AuditDecision, AuditStatus, DossierStatus
)
from .serializers import (
    DossierCreateSerializer,
    AuditSerializer, AuditUpdateSerializer,
    ContentieuxCreateSerializer, ContentieuxSerializer,
    DocumentSerializer, DossierATMPSerializer
)
from .services import ContentieuxService
from .permissions import IsSafetyManager, IsJurist, IsSuperuserOrEmployee, IsRH, IsQSE, IsDirection
from users.models import UserRole

logger = logging.getLogger(__name__)


# --- RootAPIView class for the root URL ---
class RootAPIView(APIView):
    """
    Welcome to the ATMP API Root.
    Use the links below to explore available resources.
    - ✅ Allowed
    - 🔐 Auth
    - 📌 Clickable URL
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        api_url = reverse('atmp_app:root', request=request, format=format) # Corrected: should point to the CustomAPIRootView itself
        
        return Response({
            'message': '🎉 ATMP APIs opérationnel !',
            '✅ api_root': {
                'description': 'Main API entry point with all endpoints',
                '📌 ATMP API URLs': f'🔥 {api_url} 🔥',
            },
            '✅ authentication': {
                '📌 register': reverse('atmp_app:auth-register', request=request),
                '📌 login': reverse('atmp_app:auth-login', request=request),
                '📌 profile': reverse('atmp_app:auth-profile', request=request),
                '📌 logout': reverse('atmp_app:auth-logout', request=request),
            },
            'extras': {
                '🔐 superuser admin panel': request.build_absolute_uri('/admin/'),
                '📌 back to dashboard': reverse('atmp_app:dashboard', request=request), # Assuming 'dashboard' is a template view, not an API endpoint in atmp_app
                '📌 github_repo': 'https://github.com/isaacaisha/atmp'
            }
        }, status=status.HTTP_200_OK)


# --- Custom API Views (for browsable API root) ---
class AllEndpointsView(APIRootView):
    """
    Welcome to the ATMP API All Endpoints.
    Use the links below to explore available resources.
    - 🔐 Auth    
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({
            '🔐 resources': {
                'dossiers': {
                    'list_create': reverse('atmp_app:dossier-list', request=request),
                    #'retrieve_update_delete': reverse('atmp_app:dossier-detail', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
                },
                'contentieux': {
                    'list_create': reverse('atmp_app:contentieux-list', request=request),
                    #'retrieve_update_delete': reverse('atmp_app:contentieux-detail', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
                },
                'audits': {
                    'list_create': reverse('atmp_app:audit-list', request=request),
                    #'retrieve_update_delete': reverse('atmp_app:audit-detail', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
                },
                'documents': {
                    'list_upload': reverse('atmp_app:document-list', request=request), # POST to this URL handles upload
                    #'retrieve_update_delete': reverse('atmp_app:document-detail', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
                },
            },
            '🔐 actions': {
                'dashboard_juridique': reverse('atmp_app:jurist_dashboard_data', request=request),
                'dashboard_rh': reverse('atmp_app:rh_dashboard_data', request=request),
                'dashboard_qse': reverse('atmp_app:qse_dashboard_data', request=request),
                'dashboard_direction': reverse('atmp_app:direction_dashboard_data', request=request),

                ## Special endpoints from @action decorators
                ## 'by_dossier' is on AuditViewSet, url_path='by-dossier/(?P<dossier_id>[^/.]+)'
                #'audit_by_dossier': reverse('atmp_app:audit-by-dossier', request=request, kwargs={'dossier_id': 0}).replace('0', '{dossier_id}'),
                ## 'finalize' is on AuditViewSet, detail=True
                #'finalize_audit': reverse('atmp_app:audit-finalize', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
                ## 'download' is on DocumentViewSet, detail=True
                #'download_document': reverse('atmp_app:document-download', request=request, kwargs={'pk': 0}).replace('0', '{pk}'),
            }
        })

class CustomDefaultRouter(DefaultRouter):
    APIRootView = AllEndpointsView


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
        # Add other roles here if they should see specific subsets
        elif user.role == UserRole.JURISTE:
            # Jurists might see dossiers linked to contentieux they manage or all
            # Example: return super().get_queryset().filter(contentieux__jurist=user)
            # For now, let's assume they see all relevant for their role context
            return super().get_queryset() # Or a more specific filter if needed
        elif user.role == UserRole.RH:
            # RH might see all dossiers, or only those related to employees they manage
            return super().get_queryset()
        elif user.role == UserRole.QSE:
            # QSE might see all dossiers related to audits
            return super().get_queryset()
        elif user.role == UserRole.DIRECTION:
            # Direction might see all dossiers
            return super().get_queryset()
        return DossierATMP.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# --- Contentieux Views ---
class ContentieuxViewSet(viewsets.ModelViewSet):
    queryset = Contentieux.objects.all().order_by('-created_at')
    serializer_class = ContentieuxSerializer
    permission_classes = [IsAuthenticated, IsJurist] # Ensure appropriate permissions

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == UserRole.JURISTE:
            # Jurists can see all contentieux or contentieux they are assigned to (if such a field exists)
            return super().get_queryset()
        return Contentieux.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return ContentieuxCreateSerializer
        return ContentieuxSerializer

    def perform_create(self, serializer):
        # When creating a contentieux, it might be related to a dossier,
        # and its status could be set here.
        serializer.save(status=ContentieuxStatus.DRAFT)


# --- Audit Views ---
class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.all().order_by('-created_at')
    serializer_class = AuditSerializer
    permission_classes = [IsAuthenticated, IsSafetyManager] # Ensure appropriate permissions

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == UserRole.SAFETY_MANAGER:
            # Safety managers can see all audits or audits they are assigned to
            return super().get_queryset()
        return Audit.objects.none()

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
    permission_classes = [IsAuthenticated] # Ensure appropriate permissions
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        # Users should only see documents they have access to, e.g., via dossiers they are involved in
        # For simplicity, if not superuser, filter by documents they uploaded
        return super().get_queryset().filter(uploaded_by=user)


    def perform_create(self, serializer):
        # uploaded_by is set in the serializer's create method
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

        # Example of how you might calculate case type distribution, needs actual data points in DossierATMP
        # case_type_distribution = DossierATMP.objects.values('accident__type_of_accident').annotate(count=Count('id'))
        case_type_distribution = [] # Placeholder if not implemented yet

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
