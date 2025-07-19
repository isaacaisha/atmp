# /home/siisi/atmp/atmp_app/urls.py

from django.urls import path, include, reverse
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

from .views_api import (
    #api_router,
    CustomAPIRootView,
    AuditByDossierIdView,
    AuditFinalizeView,
    get_jurist_dashboard_data,
    get_rh_dashboard_data,
    get_qse_dashboard_data,
    get_direction_dashboard_data,
    DocumentUploadView,
    DocumentDownloadView,
    DossierATMPViewSet,
    ContentieuxViewSet,
    AuditViewSet,
    DocumentViewSet,
    RootAPIView,
    CustomDefaultRouter,
    #ATMPIncidentViewSet,
    #ATMPDocumentViewSet,
)
from .views import (
    DashboardView,
    IncidentCreateView,
    IncidentListView,
    IncidentDetailView,
    IncidentUpdateView,
    IncidentDeleteView,
)
from .auth_views import AuthViewSet

app_name = 'atmp_app'

## Create the router
router = CustomDefaultRouter()
router.register(r'auth',      AuthViewSet,          basename='auth')
#router.register(r'root',      RootAPIView,          basename='root')
#router.register(r'incidents', ATMPIncidentViewSet,  basename='incident-api')
#router.register(r'documents', ATMPDocumentViewSet,  basename='document')
router.register(r'dossiers', DossierATMPViewSet, basename='dossier')
router.register(r'contentieux', ContentieuxViewSet, basename='contentieux')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    # 1) API root & all ViewSets under /atmp/api/
    #path('api/', include((api_router.urls, amtp_app), namespace=amtp_app)),
    path('api/', include(router.urls)),

    # 2) Function & class‐based endpoints not in a ViewSet
    path('api/dashboard/juridique/',  get_jurist_dashboard_data, name='jurist_dashboard_data'),
    path('api/dashboard/rh/',        get_rh_dashboard_data,       name='rh_dashboard_data'),
    path('api/dashboard/qse/',       get_qse_dashboard_data,      name='qse_dashboard_data'),
    path('api/dashboard/direction/', get_direction_dashboard_data,name='direction_dashboard_data'),
    path('api/audits/<int:dossier_id>/', AuditByDossierIdView.as_view(), name='audit-by-dossier'),
    path('api/audits/<int:audit_id>/finalize/', AuditFinalizeView.as_view(), name='audit-finalize'),
    path('api/documents/upload/',    DocumentUploadView.as_view(),   name='document-upload'),
    path('api/documents/<int:document_id>/download/', DocumentDownloadView.as_view(), name='document-download'),

    # 3) Your HTML dashboard, incidents, etc.
    path('', RedirectView.as_view(pattern_name='atmp_app:dashboard', permanent=False)),
    path('dashboard/',  DashboardView.as_view(),    name='dashboard'),
    path('incidents/',  IncidentListView.as_view(), name='incident-list'),
    path('incidents/create/', IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/<int:pk>/', IncidentDetailView.as_view(), name='incident-detail'),
    path('incidents/<int:pk>/edit/',   IncidentUpdateView.as_view(), name='incident-update'),
    path('incidents/<int:pk>/delete/', IncidentDeleteView.as_view(), name='incident-delete'),
]
