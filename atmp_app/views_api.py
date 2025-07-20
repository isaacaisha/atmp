# /home/siisi/atmp/atmp_app/views_api.py

import logging
from rest_framework import generics, status, viewsets, mixins
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone


from .models import (
    Audit, Contentieux, Document, DossierATMP,
    AuditDecision, AuditStatus, DossierStatus, UploadedFile
)
from .serializers import (
    DossierCreateSerializer, AuditSerializer, AuditUpdateSerializer,
    ContentieuxSerializer, DocumentSerializer, DossierATMPSerializer, UploadedFileSerializer
)
from .services import ContentieuxService
from .permissions import IsSafetyManager, IsJurist

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
    queryset = DossierATMP.objects.all().order_by('-created_at')
    serializer_class = DossierATMPSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'safety_manager']
    search_fields = ['reference', 'title']

    def perform_create(self, serializer):
        reference = f"DAT-{int(timezone.now().timestamp())}"
        serializer.save(reference=reference, created_by=self.request.user)


# For Dossier create view
class DossierCreateView(generics.CreateAPIView):
    serializer_class = DossierCreateSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            reference=f"DAT-{int(timezone.now().timestamp())}"
        )


# For Dossier detail view
class DossierDetailView(generics.RetrieveAPIView):
    queryset = DossierATMP.objects.select_related(
        'contentieux',
        'audit',
        'tiers'
    ).prefetch_related(
        'temoins',
        'documents',
        'contentieux__documents',
        'contentieux__juridiction_steps'
    )
    serializer_class = DossierATMPSerializer


# --- Contentieux Views (APIView subclasses) ---
class ContentieuxViewSet(viewsets.ModelViewSet):
    queryset = Contentieux.objects.all().order_by('-created_at')
    serializer_class = ContentieuxSerializer
    permission_classes = [IsAuthenticated, IsJurist]
    filterset_fields = ['status']
    search_fields = ['reference']

    def perform_create(self, serializer):
        reference = f"CONT-{int(timezone.now().timestamp())}"
        serializer.save(reference=reference, status=ContentieuxStatus.DRAFT)


class ContentieuxDetailView(APIView):
    def get(self, request, contentieux_id):
        try:
            contentieux = ContentieuxService.get_contentieux_by_id(contentieux_id)
            if not contentieux:
                return Response({"message": 'Contentieux non trouvé'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ContentieuxSerializer(contentieux)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching contentieux by ID: {e}")
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContentieuxCreateView(APIView):
    def post(self, request):
        try:
            reference = f"CONT-{int(datetime.now().timestamp())}"
            new_contentieux_data = {
                **request.data,
                'reference': reference,
                'status': ContentieuxStatus.DRAFT.value,
            }
            serializer = ContentieuxSerializer(data=new_contentieux_data)
            if serializer.is_valid():
                contentieux = serializer.save()
                return Response(ContentieuxSerializer(contentieux).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erreur lors de la création du contentieux: {e}")
            return Response({"message": "Erreur lors de la création du dossier", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Audit Views (APIView subclasses) ---
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
        decision_value = request.data.get('decision')
        
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
        
        audit.status = AuditStatus.COMPLETED
        audit.decision = decision.value
        audit.completed_at = timezone.now()
        audit.save()

        dossier = audit.dossier_atmp
        dossier.status = DossierStatus.ANALYSE_EN_COURS
        dossier.save()

        if decision == AuditDecision.CONTEST:
            new_contentieux = ContentieuxService.create_from_audit(audit, dossier)
            return Response({
                "message": "Audit finalized and litigation created",
                "contentieux": ContentieuxSerializer(new_contentieux).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "message": "Audit finalized successfully"
        }, status=status.HTTP_200_OK)


# For Audit update view
class AuditUpdateView(generics.UpdateAPIView):
    queryset = Audit.objects.all()
    serializer_class = AuditUpdateSerializer


class AuditFinalizeView(APIView):
    def post(self, request, audit_id):
        try:
            decision_value = request.data.get('decision')
            if not decision_value:
                return Response({"message": "La décision est requise pour finaliser l'audit."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                decision = AuditDecision(decision_value)
            except ValueError:
                return Response({"message": "Décision invalide."}, status=status.HTTP_400_BAD_REQUEST)

            audit = Audit.objects.get(id=audit_id)
            if audit.status == AuditStatus.COMPLETED.value:
                return Response({"message": "Cet audit est déjà clôturé."}, status=status.HTTP_400_BAD_REQUEST)

            audit.status = AuditStatus.COMPLETED.value
            audit.decision = decision.value
            audit.completed_at = timezone.now()
            audit.save()

            dossier = audit.dossier_atmp
            dossier.status = DossierStatus.ANALYSE_EN_COURS.value
            dossier.save()

            new_contentieux = None
            if decision == AuditDecision.CONTEST:
                new_contentieux = ContentieuxService.create_from_audit(audit, dossier)
                contentieux_serializer = ContentieuxSerializer(new_contentieux)
                return Response({
                    "message": "Audit finalisé et contentieux créé avec succès.",
                    "audit": AuditSerializer(audit).data,
                    "contentieux": contentieux_serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                "message": "Audit finalisé avec succès.",
                "audit": AuditSerializer(audit).data
            }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response({"message": "Audit ou dossier parent non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            logger.error(f"Validation error finalizing audit: {e.message_dict}")
            return Response({"message": "Erreur de validation des données.", "details": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erreur lors de la finalisation de l'audit: {e}")
            return Response({"message": "Erreur interne du serveur"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Document Views (APIView subclasses) ---
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def perform_create(self, serializer):
        serializer.save(
            uploaded_by=self.request.user,
            mime_type=self.request.FILES['file'].content_type,
            size=self.request.FILES['file'].size
        )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        try:
            return FileResponse(
                document.file.open(),
                as_attachment=True,
                filename=document.original_name
            )
        except FileNotFoundError:
            return Response(
                {"message": "File not found on server"},
                status=status.HTTP_404_NOT_FOUND
            )


class DocumentUploadView(generics.CreateAPIView):
    parser_classes = [MultiPartParser]
    serializer_class = DocumentSerializer


class DocumentDownloadView(APIView):
    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id)
            file_path = document.file.path

            if not os.path.exists(file_path):
                raise Http404("Fichier non trouvé sur le serveur.")

            response = FileResponse(open(file_path, 'rb'), content_type=document.mime_type)
            response = f'attachment; filename="{document.original_name}"' # Correct header
            return response
        except ObjectDoesNotExist:
            return Response({"message": "Document non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Http404 as e:
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return Response({"message": "Erreur lors du téléchargement du document."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='juridique')
    def jurist_dashboard(self, request):
        # Implement actual dashboard logic
        return Response({"message": "Jurist dashboard data"})

    @action(detail=False, methods=['get'], url_path='rh')
    def rh_dashboard(self, request):
        # Implement actual dashboard logic
        return Response({"message": "HR dashboard data"})

    @action(detail=False, methods=['get'], url_path='direction')
    def management_dashboard(self, request):
        try:
            open_dossiers = DossierATMP.objects.exclude(
                status=DossierStatus.CLOTURE_SANS_SUITE.value
            ).count()
            
            total_dossiers = DossierATMP.objects.count()
            estimated_risk_per_case = 5000
            total_risk_value = open_dossiers * estimated_risk_per_case

            return Response({
                "stats": {
                    "openDossiers": open_dossiers,
                    "totalDossiers": total_dossiers,
                    "totalRiskValue": total_risk_value,
                }
            })
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return Response(
                {"message": "Error retrieving dashboard data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# --- UploadedFile ViewSet (Django ORM) ---
class UploadedFileViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]
    #parser_classes = (MultiPartParser, FormParser) # Needed for file uploads


    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        try:
            document = UploadedFile.objects.get(pk=pk)
            if not document.path or not os.path.exists(document.path):
                raise Http404("Document non trouvé ou chemin invalide.")

            mime_type, _ = mimetypes.guess_type(document.path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            response = FileResponse(open(document.path, 'rb'), content_type=mime_type)
            response['Content-Disposition'] = f'attachment; filename="{document.original_name}"'
            return response

        except UploadedFile.DoesNotExist:
            raise Http404("Document non trouvé.")
        except Exception as e:
            print(f"Erreur lors du téléchargement du document: {e}")
            return Response({'message': f"Erreur interne du serveur: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- DossierATMP Views (function-based, now DRF @api_view) ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dossiers_view(request):
    """
    GET or POST /atmp/api/dossiers/
    """
    if request.method == 'POST':
        data = {**request.data, 'reference': f"DAT-{int(datetime.now().timestamp())}"}
        serializer = DossierATMPSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        dossier = serializer.save()
        return Response(DossierATMPSerializer(dossier).data, status=status.HTTP_201_CREATED)

    elif request.method == 'GET':
        dossiers = DossierATMP.objects.all().order_by('-created_at')
        serialized = DossierATMPSerializer(dossiers, many=True)
        return Response(serialized.data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def create_dossier(request):
    if request.method == 'GET':
        return Response({'detail': 'Use POST to create a Dossier.'})

    """
    POST /atmp/api/dossiers/
    """
    # inject a reference on the fly
    data = {**request.data, 'reference': f"DAT-{int(datetime.now().timestamp())}"}
    serializer = DossierATMPSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    dossier = serializer.save()
    return Response(DossierATMPSerializer(dossier).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_dossiers(request):
    """
    GET /atmp/api/dossiers/all/
    """
    dossiers = DossierATMP.objects.all().order_by('-created_at')
    serialized = DossierATMPSerializer(dossiers, many=True)
    return Response(serialized.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dossier_by_id(request, dossier_id):
    """
    GET /atmp/api/dossiers/<dossier_id>/
    """
    try:
        dossier = DossierATMP.objects.get(id=dossier_id)
    except DossierATMP.DoesNotExist:
        return Response({'message': 'Dossier non trouvé.'}, status=status.HTTP_404_NOT_FOUND)
    serialized = DossierATMPSerializer(dossier)
    return Response(serialized.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_jurist_dashboard_data(request):
    """
    GET /atmp/api/dashboard/juridique/
    """
    return Response(
        {"message": "Jurist dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_rh_dashboard_data(request):
    """
    GET /atmp/api/dashboard/rh/
    """
    return Response(
        {"message": "RH dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_qse_dashboard_data(request):
    """
    GET /atmp/api/dashboard/qse/
    """
    return Response(
        {"message": "QSE dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
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

        # If you later need real case-type distribution, query your JSONField here.
        case_type_distribution = []

        return Response({
            "stats": {
                "openDossiers": open_dossiers,
                "totalDossiers": total_dossiers,
                "totalRiskValue": total_risk_value,
            },
            "caseTypeDistribution": case_type_distribution,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données du tableau de bord Direction: {e}")
        return Response(
            {"message": "Erreur lors de la récupération des données du tableau de bord Direction."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
