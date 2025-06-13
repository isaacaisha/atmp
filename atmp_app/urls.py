# /home/siisi/atmp/atmp_app/urls.py

from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from .views import (
    ATMPIncidentViewSet, ATMPDocumentViewSet,
    DashboardView,
    IncidentListView, IncidentDetailView, IncidentCreateView,
)

app_name = 'atmp_app'

# Set up DRF router
router = DefaultRouter()
router.register(r'incidents', ATMPIncidentViewSet, basename='incident')
router.register(r'documents', ATMPDocumentViewSet, basename='document')

urlpatterns = [
    # Redirect root of this app to dashboard
    path('', RedirectView.as_view(pattern_name='atmp_app:dashboard', permanent=False)),

    # HTML pages
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('incidents/create/',   IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/',          IncidentListView.as_view(),   name='incident-list'),
    path('incidents/<int:pk>/', IncidentDetailView.as_view(), name='incident-detail'),

    # API endpoints
    path('api/', include((router.urls, 'atmp_api'), namespace='api')),
]
