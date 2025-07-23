# /home/siisi/atmp/atmp_app/urls.py

from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from .auth_views import AuthViewSet

from .views_api import (
    AllEndpointsView,
    CustomDefaultRouter,
    DossierViewSet,
    ContentieuxViewSet,
    AuditViewSet,
    DocumentViewSet,
    get_jurist_dashboard_data,
    get_rh_dashboard_data,
    get_qse_dashboard_data,
    get_direction_dashboard_data
)

from .views import (
    DashboardView,
    ProfileView,
    IncidentCreateView,
    IncidentListView,
    IncidentDetailView,
    IncidentUpdateView,
    IncidentDeleteView,
    ContentieuxCreateView,
    DocumentUploadView,
    DocumentDeleteView,
    JuridiqueDashboardHTMLView,
    RHDashboardHTMLView,
    QSEDashboardHTMLView,
    DirectionDashboardHTMLView
)

app_name = 'atmp_app'

# Create the custom router
router = CustomDefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'dossiers', DossierViewSet, basename='dossier')
router.register(r'contentieux', ContentieuxViewSet, basename='contentieux')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    # ─── API ───────────────────────────────────────────────────────
    path('api/', include(router.urls)),
    # API Dashboard endpoints (keeping these as function views for specific data access)
    path('api/root', AllEndpointsView.as_view(), name='root'),
    path('api/dashboard/juridique/', get_jurist_dashboard_data, name='jurist_dashboard_data'),
    path('api/dashboard/rh/', get_rh_dashboard_data, name='rh_dashboard_data'),
    path('api/dashboard/qse/', get_qse_dashboard_data, name='qse_dashboard_data'),
    path('api/dashboard/direction/', get_direction_dashboard_data, name='direction_dashboard_data'),
    
    # ─── HTML frontend ────────────────────────────────────────────
    path('', RedirectView.as_view(pattern_name='atmp_app:dashboard', permanent=False)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('incidents/', IncidentListView.as_view(), name='incident-list'),
    path('incidents/create/', IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/<int:pk>/', IncidentDetailView.as_view(), name='incident-detail'),
    path('incidents/<int:pk>/edit/', IncidentUpdateView.as_view(), name='incident-update'),
    path('incidents/<int:pk>/delete/', IncidentDeleteView.as_view(), name='incident-delete'),
    
    # Contentieux routes
    path('incidents/<int:dossier_pk>/contentieux/create/', ContentieuxCreateView.as_view(), name='contentieux-create'),
    
    # Document routes (HTML view for document upload)
    path('incidents/<int:incident_pk>/documents/upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),

    # HTML Dashboard Actions Routes
    path('dashboard/juridique/', JuridiqueDashboardHTMLView.as_view(), name='dashboard-juridique'),
    path('dashboard/rh/', RHDashboardHTMLView.as_view(), name='dashboard-rh'),
    path('dashboard/qse/', QSEDashboardHTMLView.as_view(), name='dashboard-qse'),
    path('dashboard/direction/', DirectionDashboardHTMLView.as_view(), name='dashboard-direction'),
]
