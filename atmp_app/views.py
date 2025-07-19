# /home/siisi/atmp/atmp_app/views_api.py

from rest_framework import viewsets, renderers, parsers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import action, api_view, permission_classes

from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.http import FileResponse, Http404
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from datetime import datetime
import os, logging

from .mixins import ProviderOrSuperuserMixin, EmployeeRequiredMixin, SafetyManagerMixin
from .models import (
    DossierATMP, Contentieux, Audit, Document,
    AuditDecision, AuditStatus, ContentieuxStatus,
    DossierStatus, DocumentType
)
from .serializers import (
    DossierATMPSerializer, ContentieuxSerializer,
    AuditSerializer, DocumentSerializer
)
from .permissions import IsProvider
from .services import ContentieuxService
from users.models import CustomUser



from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied

from .forms import ContentieuxForm

from dashboard.views import (
    custom_permission_denied_view,
    custom_page_not_found_view
)

logger = logging.getLogger(__name__)


# ─── 1) Custom API Root ────────────────────────────────────────────────
class CustomAPIRootView(APIRootView):
    """
    Overrides the DRF‐generated /atmp/api/ root.
    Lists all registered ViewSet endpoints.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({
            "authentication": {
                "register": reverse('atmp_app:auth-register', request=request),
                "login":    reverse('atmp_app:auth-login',    request=request),
                "logout":   reverse('atmp_app:auth-logout',   request=request),
                "profile":  reverse('atmp_app:auth-profile',  request=request),
            },
            "resources": {
                "contentieux": reverse('atmp_app:contentieux-list', request=request),
                "dossiers":    reverse('atmp_app:dossier-list',      request=request),
                "audits":      reverse('atmp_app:audit-list',       request=request),
                "documents":   reverse('atmp_app:document-list',    request=request),
            },
            "actions": {
                "finalize_audit": reverse('atmp_app:audit-finalize', request=request, kwargs={'pk': 0}).replace('0', '{audit_id}'),
                "download_document": reverse('atmp_app:document-download', request=request, kwargs={'pk': 0}).replace('0', '{document_id}'),
                "dashboard_juridique": reverse('atmp_app:jurist_dashboard_data', request=request),
                "dashboard_rh":        reverse('atmp_app:rh_dashboard_data',    request=request),
                "dashboard_qse":       reverse('atmp_app:qse_dashboard_data',   request=request),
                "dashboard_direction": reverse('atmp_app:direction_dashboard_data', request=request),
            }
        })


# ─── 2) Dossier ViewSet ────────────────────────────────────────────────
class DashboardView(TemplateView):
    """
    Simple dashboard/home view for logged-in users.
    """
    login_url = reverse_lazy('users:login')
    redirect_field_name = 'next'
    template_name = 'atmp_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            # count the dossiers that this user created
            ctx['incidents_count'] = DossierATMP.objects.filter(created_by=user).count()
        else:
            ctx['incidents_count'] = 0
        return ctx


class IncidentCreateView(LoginRequiredMixin, ProviderOrSuperuserMixin, CreateView):
    """
    HTML View: Form to report a new ATMP incident.
    Accessible to both employees and superusers.
    Automatically sets provider to the current user.
    """
    model = Contentieux
    form_class = ContentieuxForm
    template_name = 'atmp_app/incident_form.html'
    success_url = reverse_lazy('atmp_app:incident-list')

    def test_func(self):
        """Allow access to employees and superusers"""
        user = self.request.user
        return user.is_superuser or user.role == 'employee'

    def form_valid(self, form):
        """Handle form submission"""
        form.instance.provider = self.request.user
        response = super().form_valid(form)
        document = form.cleaned_data.get('document')
        if document:
            Document.objects.create(
                incident=self.object,
                uploaded_by=self.request.user,
                file=document,
            )
        return response


class IncidentUpdateView(LoginRequiredMixin, ProviderOrSuperuserMixin, UpdateView):
    """
    HTML View: Allow employees to update their own incidents.
    """
    model = Contentieux
    form_class = ContentieuxForm
    template_name = 'atmp_app/incident_form.html'
    context_object_name = 'incident'

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        document = form.cleaned_data.get('document')
        if document:
            Document.objects.create(
                incident=self.object,
                uploaded_by=self.request.user,
                file=document,
            )
        return super().form_valid(form)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Contentieux.objects.all()
        return Contentieux.objects.filter(provider=user)


class IncidentDeleteView(LoginRequiredMixin, ProviderOrSuperuserMixin, DeleteView):
    """
    HTML View: Allow employees to delete their own incidents.
    """
    model = Contentieux
    template_name = 'atmp_app/incident_confirm_delete.html'
    success_url = reverse_lazy('atmp_app:incident-list')
    context_object_name = 'incident'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Contentieux.objects.all()
        return Contentieux.objects.filter(provider=user)


class IncidentListView(LoginRequiredMixin, ListView):
    """
    HTML View: List all incidents for the logged-in user.
    Employees see their own reports; safety managers see incidents assigned to them.
    """
    model = Contentieux
    template_name = 'atmp_app/incident_list.html'
    context_object_name = 'incidents'

    def get_queryset(self):
        user = self.request.user
        qs = Contentieux.objects.select_related('dossier_atmp')
        if user.is_superuser:
            return qs
        if user.role == 'employee':
            # employees see contentieux for dossiers they created
            return qs.filter(dossier_atmp__created_by=user)
        # safety managers see contentieux for dossiers assigned to them
        return qs.filter(dossier_atmp__safety_manager=user)


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Contentieux
    template_name = 'atmp_app/incident_detail.html'
    context_object_name = 'incident'

    def get_object(self, queryset=None):
        instance = super().get_object(queryset)
        user = self.request.user
        if user.is_superuser:
            return instance
        # employee → must be creator of the dossier
        if user.role == 'employee' and instance.dossier_atmp.created_by != user:
            raise PermissionDenied
        # safety_manager → must match dossier_atmp.safety_manager
        if user.role == 'safety_manager' and instance.dossier_atmp.safety_manager != user:
            raise PermissionDenied
        return instance
            

class DossierATMPViewSet(viewsets.ModelViewSet):
    queryset = DossierATMP.objects.all().order_by('-created_at')
    serializer_class = DossierATMPSerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = [renderers.JSONRenderer, renderers.BrowsableAPIRenderer]


# ─── 3) Contentieux, Audit, Document ViewSets ─────────────────────────
class ContentieuxViewSet(viewsets.ModelViewSet):
    queryset = Contentieux.objects.all().order_by('-created_at')
    serializer_class = ContentieuxSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(
            reference=str(f"CONT-{int(datetime.now().timestamp())}"),
            status=ContentieuxStatus.DRAFT.value
        )


class AuditViewSet(viewsets.ModelViewSet):
    queryset = Audit.objects.all().order_by('-created_at')
    serializer_class = AuditSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        # Delegate to your APIView logic
        view = AuditFinalizeView.as_view()
        return view(request._request, audit_id=pk)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        view = DocumentDownloadView.as_view()
        return view(request._request, document_id=pk)
