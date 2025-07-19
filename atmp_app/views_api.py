# /home/siisi/atmp/atmp_app/views_api.py

from rest_framework import status, viewsets, renderers, parsers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.reverse import reverse # Needed for CustomAPIRootView if you customize it
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.text import slugify
import os
from datetime import datetime, timezone
import logging
from django.conf import settings
from django.http import FileResponse, Http404
from django.db.models import Count # Import Count for aggregation

from.models import (
    ContentieuxStatus, Audit, Contentieux, Document, DossierATMP,
    AuditDecision, AuditStatus, DossierStatus, DocumentType
)
from.serializers import (
    AuditSerializer, ContentieuxSerializer,
    DocumentSerializer, DossierATMPSerializer
)
from.services import ContentieuxService

from users.models import CustomUser
from .auth_views import AuthViewSet

logger = logging.getLogger(__name__)


# --- Custom API Views (for browsable API root) ---
class CustomAPIRootView(APIRootView):
    def get(self, request, *args, **kwargs):
        return Response({
            # Authentication
            'authentication': {
                #'users': reverse('atmp_app:user-list', request=request),
                'register': reverse('atmp_app:auth-register', request=request),
                'login': reverse('atmp_app:auth-login', request=request),
                'profile': reverse('atmp_app:auth-profile', request=request),
                'logout': reverse('atmp_app:auth-logout', request=request),
            },
            'resources': {
                # Main resources
                #'users': reverse('atmp_app:user-list', request=request),
                'dossiers': reverse('atmp_app:dossier-list', request=request),
                'contentieux': reverse('atmp_app:contentieux-list', request=request),
                'audits': reverse('atmp_app:audit-list', request=request),
                'documents': reverse('atmp_app:document-list', request=request),
            },
            'actions': {
                # Dashboard endpoints
                'dashboard_juridique': reverse('atmp_app:jurist_dashboard_data', request=request),
                'dashboard_rh': reverse('atmp_app:rh_dashboard_data', request=request),
                'dashboard_qse': reverse('atmp_app:qse_dashboard_data', request=request),
                'dashboard_direction': reverse('atmp_app:direction_dashboard_data', request=request),

                # Special endpoints
                #'audit_by_dossier': reverse('atmp_app:audit-by-dossier', request=request, kwargs={'dossier_id': 0}).replace('0', '{dossier_id}'),
                #'finalize_audit': reverse('atmp_app:finalize-audit', request=request, kwargs={'audit_id': 0}).replace('0', '{audit_id}'),
                #'upload_document': reverse('atmp_app:upload_document', request=request),
                #'download_document': reverse('atmp_app:download_document', request=request, kwargs={'document_id': 0}).replace('0', '{document_id}'),
            },
            'extras': {
                'dashboard': reverse('atmp_app:dashboard', request=request),
                'superuser_login': request.build_absolute_uri('/admin/'),
                'github_repo': 'https://github.com/isaacaisha/atmp'
            },
        })

class CustomDefaultRouter(DefaultRouter):
    APIRootView = CustomAPIRootView


# --- RootAPIView class for the root URL ---
class RootAPIView(APIView):
    """
    Welcome to the Praevia (Gemini) API Root.
    Use the links below to explore available resources.
    - 🔐 gemini_api_url 
    - 📌 API Root (clickable URL)
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        api_url = reverse('atmp_app:root_api', request=request, format=format)
        
        return Response({
            'message': '🎉 Django Backend Praevia (Gemini) opérationnel !',
            'available_endpoints': {
                'message': '1.register, 2.login & 3.enjoy !',
                '1.users': reverse('atmp_app:user-list', request=request),
                '2.login': reverse('atmp_app:login', request=request)
            },
            'api_root': {
                'description': 'Main API entry point with all endpoints',
                '3.atmp_app_url': f'🔥 {api_url} 🔥',
                '4. superuser_login': request.build_absolute_uri('/admin/'),
                '5. github_repo': 'https://github.com/isaacaisha/praevia_gemini'
            },
        }, status=status.HTTP_200_OK)


# --- Dossier Views ---
class DossierATMPViewSet(viewsets.ModelViewSet):
    queryset = DossierATMP.objects.all().order_by('-created_at')
    serializer_class = DossierATMPSerializer
    permission_classes = [IsAuthenticated]
    
    # Use DRF's default renderer classes
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
    ]


# --- Audit Views (APIView subclasses) ---
class AuditByDossierIdView(APIView):
    def get(self, request, dossier_id):
        try:
            dossier = DossierATMP.objects.get(id=dossier_id)
            audit = dossier.audit_detail # Accessing the reverse relation
            serializer = AuditSerializer(audit)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"message": "Aucun audit trouvé pour ce dossier ou dossier AT/MP non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'audit: {e}")
            return Response({"message": "Erreur interne du serveur"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuditUpdateView(APIView):
    def put(self, request, audit_id):
        try:
            audit = Audit.objects.get(id=audit_id)
            serializer = AuditSerializer(audit, data=request.data, partial=True)
            if serializer.is_valid():
                updated_audit = serializer.save()

                dossier = updated_audit.dossier_atmp
                dossier.status = updated_audit.status
                dossier.save()

                return Response(AuditSerializer(updated_audit).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response({"message": "Audit non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            logger.error(f"Validation error updating audit: {e.message_dict}")
            return Response({"message": "Erreur de validation des données.", "details": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'audit: {e}")
            return Response({"message": "Erreur interne du serveur"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


# --- Contentieux Views (APIView subclasses) ---
class ContentieuxListView(APIView):
    def get(self, request):
        try:
            result = ContentieuxService.get_all_contentieux(request.query_params)
            serializer = ContentieuxSerializer(result, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching all contentieux: {e}")
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_jurist_dashboard_data(request):
    """
    GET /praevia/api/dashboard/juridique/
    """
    return Response(
        {"message": "Jurist dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_rh_dashboard_data(request):
    """
    GET /praevia/api/dashboard/rh/
    """
    return Response(
        {"message": "RH dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_qse_dashboard_data(request):
    """
    GET /praevia/api/dashboard/qse/
    """
    return Response(
        {"message": "QSE dashboard data (not implemented)"},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_direction_dashboard_data(request):
    """
    GET /praevia/api/dashboard/direction/
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


# --- Document Views (APIView subclasses) ---
class DocumentUploadView(APIView):
    def post(self, request):
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response({"message": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

            contentieux_id = request.data.get('contentieuxId')
            uploaded_by_id = request.data.get('uploadedBy')
            document_type_value = request.data.get('documentType')

            if not all([contentieux_id, uploaded_by_id, document_type_value]):
                return Response({"message": "Missing required document fields (contentieuxId, uploadedBy, documentType)."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                contentieux = Contentieux.objects.get(id=contentieux_id)
                uploaded_by = CustomUser.objects.get(id=uploaded_by_id)
                document_type = DocumentType(document_type_value).value
            except (ObjectDoesNotExist, ValueError) as e:
                return Response({"message": f"Invalid ID or DocumentType: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            new_document = Document(
                contentieux=contentieux,
                uploaded_by=uploaded_by,
                document_type=document_type,
                original_name=uploaded_file.name,
                file=uploaded_file,
                mime_type=uploaded_file.content_type,
                size=uploaded_file.size
            )
            new_document.full_clean()
            new_document.save()

            contentieux.documents.add(new_document)
            contentieux.save()

            serializer = DocumentSerializer(new_document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.error(f"Validation error uploading document: {e.message_dict}")
            return Response({"message": "Erreur de validation des données.", "details": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return Response({"message": "Erreur lors de l'upload du document."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


# --- DossierATMP Views (function-based, now DRF @api_view) ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dossiers_view(request):
    """
    GET or POST /praevia/api/dossiers/
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
    POST /praevia/api/dossiers/
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
    GET /praevia/api/dossiers/all/
    """
    dossiers = DossierATMP.objects.all().order_by('-created_at')
    serialized = DossierATMPSerializer(dossiers, many=True)
    return Response(serialized.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dossier_by_id(request, dossier_id):
    """
    GET /praevia/api/dossiers/<dossier_id>/
    """
    try:
        dossier = DossierATMP.objects.get(id=dossier_id)
    except DossierATMP.DoesNotExist:
        return Response({'message': 'Dossier non trouvé.'}, status=status.HTTP_404_NOT_FOUND)
    serialized = DossierATMPSerializer(dossier)
    return Response(serialized.data, status=status.HTTP_200_OK)


class ContentieuxViewSet(viewsets.ModelViewSet):
    queryset = Contentieux.objects.all()
    serializer_class = ContentieuxSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        reference = f"CONT-{int(datetime.now().timestamp())}"
        request.data['reference'] = reference
        request.data['status'] = ContentieuxStatus.DRAFT.value
        return super().create(request, *args, **kwargs)


class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        return AuditFinalizeView.as_view()(request._request, pk)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        return DocumentDownloadView.as_view()(request._request, pk)


## ─── Router setup ───────────────────────────────────────────────────
#class CustomDefaultRouter(DefaultRouter):
#    APIRootView = CustomAPIRootView
#
#
## Expose a single router instance your urls.py will include
#api_router = CustomDefaultRouter()
#api_router.register(r'auth',       AuthViewSet,        basename='auth')
#api_router.register(r'dossiers',   DossierATMPViewSet, basename='dossier')
#api_router.register(r'contentieux', ContentieuxViewSet, basename='contentieux')
#api_router.register(r'audits',      AuditViewSet,       basename='audit')
#api_router.register(r'documents',   DocumentViewSet,    basename='document')




#from rest_framework import mixins, viewsets, status
#from rest_framework.permissions import AllowAny, IsAuthenticated
#from rest_framework.views import APIView
#from rest_framework.response import Response
#from rest_framework.routers import DefaultRouter, APIRootView
#from rest_framework.reverse import reverse
#
#from .models import ATMPIncident, ATMPDocument
#from .auth_serializers import EmptySerializer
#from .serializers import ATMPIncidentSerializer, ATMPDocumentSerializer
#from .permissions import IsProvider
#
#from users.models import CustomUser
#
#
## ---------------------- API ViewSets (DRF) ----------------------
#
## --- Custom API Views (for browsable API root) ---
## This class will be the actual browsable API root at /atmp/api/
#class CustomAPIRootView(APIRootView): # Changed from BaseAPIRootView to CustomAPIRootView
#    """
#    Welcome to the ATMP API Root.
#    Use the links below to explore available resources.
#    - 📌 Clickable URL
#    """
#    permission_classes = [AllowAny]
#    
#    # api_root_dict will be populated by CustomDefaultRouter
#    # No need to explicitly initialize it here, as it's set by the router instance.
#
#    def get(self, request, format=None):
#        # The main API root URL is typically named 'api-root' when included via a router.
#        current_api_root_url = reverse('atmp_app:root-list', request=request, format=format)
#        dashboard_url = reverse('atmp_app:dashboard', request=request, format=format)
#        admin_panel_url = request.build_absolute_uri('/admin/')
#        
#        return Response({
#            'authentication': { # Re-add authentication links if desired
#                'message': '1.register, 2.login, 3.profile, 4.logout',
#                '1.)register': reverse('atmp_app:auth-register', request=request),
#                '2.)login':    reverse('atmp_app:auth-login',    request=request),
#                '3.)profile':  reverse('atmp_app:auth-profile',  request=request),
#                '4.)logout':   reverse('atmp_app:auth-logout',   request=request)
#            },
#            'message': '🎉 Django Backend AMP opérationnel !',
#            '🔐 api_root_data': {
#                'description': 'Main API entry point with all endpoints',
#                '1.)API Root URL': f'🔥 {current_api_root_url} 🔥',
#            },
#            'external_resources': {
#                'description': '🔐 1.superuser admin panel, 2.back to dashboard, 3.github repository',
#                '1.)superuser admin panel': f'🔥 {admin_panel_url} 🔥',
#                '2.)back to dashboard': f'🔥 {dashboard_url} 🔥',
#                '3.)github_repo': 'https://github.com/isaacaisha/atmp'
#            },
#        }, status=status.HTTP_200_OK)
#
#
#class CustomDefaultRouter(DefaultRouter):
#    APIRootView = CustomAPIRootView # Point to your custom APIRootView
#
#    def get_api_root_view(self, api_urls=None):
#        api_root_dict = {}
#        for prefix, viewset, basename in self.registry:
#            list_route_name = f'{basename}-list' # DRF's default list view name
#            try:
#                # Use the full namespace:viewname
#                api_root_dict[f'{basename}_list'] = reverse(f'atmp_app:{list_route_name}', request=None) 
#            except Exception as e:
#                # This could happen if a viewset doesn't have a list endpoint (e.g., custom actions only)
#                print(f"Warning: Could not reverse URL for {list_route_name} (basename: {basename}). Error: {e}")
#                pass 
#        
#        # Instantiate the APIRootView and pass the api_root_dict to its instance.
#        view = self.APIRootView.as_view()
#        view.api_root_dict = api_root_dict # This is crucial for BaseAPIRootView to get the links
#        return view
#
#
## --- RootAPIView class for the root URL ---
#class RootAPIView(mixins.ListModelMixin, viewsets.GenericViewSet):
#    """
#    Use the links below to explore available resources.
#    - 🔐 atmp_api_url 
#    """
#    permission_classes = [IsAuthenticated]
#
#    def list(self, request, *args, **kwargs):
#        return Response({
#            'main_api_resources': {
#                # Main resources
#                #'users': reverse('atmp_app:user-list', request=request),
#                'incidents': reverse('atmp_app:incident-api-list', request=request),
#                'documents': reverse('atmp_app:document-list', request=request),
#                #'dossiers': reverse('atmp_app:dossier-list', request=request),
#                #'contentieux': reverse('atmp_app:contentieux-list', request=request),
#                #'audits': reverse('atmp_app:audit-list', request=request),
#            },
#            #'actions': {
#            #    # Dashboard endpoints
#            #    'dashboard_juridique': reverse('atmp_app:jurist_dashboard_data', request=request),
#            #    'dashboard_rh': reverse('atmp_app:rh_dashboard_data', request=request),
#            #    'dashboard_qse': reverse('atmp_app:qse_dashboard_data', request=request),
#            #    'dashboard_direction': reverse('atmp_app:direction_dashboard_data', request=request),
##
#            #    # Special endpoints
#            #    #'audit_by_dossier': reverse('atmp_app:audit-by-dossier', request=request, kwargs={'dossier_id': 0}).replace('0', '{dossier_id}'),
#            #    #'finalize_audit': reverse('atmp_app:finalize-audit', request=request, kwargs={'audit_id': 0}).replace('0', '{audit_id}'),
#            #    'upload_document': reverse('atmp_app:upload_document', request=request),
#            #    #'download_document': reverse('atmp_app:download_document', request=request, kwargs={'document_id': 0}).replace('0', '{document_id}'),
#            #},
#            'back_to_main_api_root': reverse('atmp_app:api-root', request=request),
#        }, status=status.HTTP_200_OK)
#
#
## --- Incident Views ---
#class ATMPIncidentViewSet(viewsets.ModelViewSet):
#    """
#    REST API endpoint for ATMP incidents.
#    Superusers and 'employee' users may create; everyone authenticated may list.
#    """
#    serializer_class = ATMPIncidentSerializer
#    permission_classes = [IsAuthenticated]
#
#    def get_permissions(self):
#        if self.action == 'create':
#            return [IsAuthenticated(), IsProvider()]
#        return [IsAuthenticated()]
#
#    def get_queryset(self):
#        user = self.request.user
#        if user.is_superuser:
#            return ATMPIncident.objects.all()
#        if user.role == 'employee':
#            return ATMPIncident.objects.filter(provider=user)
#        return ATMPIncident.objects.filter(safety_manager=user)
#
#    def perform_create(self, serializer):
#        # Automatically set the reporting user
#        serializer.save(provider=self.request.user)
#
#
## --- Document Views ---
#class ATMPDocumentViewSet(viewsets.ModelViewSet):
#    """
#    REST API endpoint for ATMP documents.
#    Authenticated users can list/upload their own documents.
#    """
#    serializer_class = ATMPDocumentSerializer
#    permission_classes = [IsAuthenticated]
#
#    def get_queryset(self):
#        user = self.request.user
#        if user.is_superuser:
#            return ATMPDocument.objects.all()
#        return ATMPDocument.objects.filter(uploaded_by=user)
#
#    def perform_create(self, serializer):
#        # Automatically set the uploader
#        serializer.save(uploaded_by=self.request.user)
#