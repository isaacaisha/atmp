# /home/siisi/atmp/atmp_app/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ATMPIncidentViewSet, ATMPDocumentViewSet,
    IncidentListView, IncidentDetailView, IncidentCreateView,
    dashboard_view
)

app_name = 'atmp_app'

router = DefaultRouter()
router.register(r'incidents', ATMPIncidentViewSet, basename='incident')
router.register(r'documents', ATMPDocumentViewSet, basename='document')

urlpatterns = [
    # HTML pages
    path('incidents/create/', IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/',        IncidentListView.as_view(),   name='incident-list'),
    path('incidents/<int:pk>/',     IncidentDetailView.as_view(), name='incident-detail'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # API under /api/
    path('api/', include((router.urls, 'atmp_api'), namespace='api')),
]
