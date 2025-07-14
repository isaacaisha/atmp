# /home/siisi/atmp/atmp_api/views.py

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter, APIRootView

from atmp_app.models import ATMPIncident, ATMPDocument
from .serializers import ATMPIncidentSerializer, ATMPDocumentSerializer
from .permissions import IsProvider

# ---------------------- API ViewSets (DRF) ----------------------

class CustomAPIRootView(APIRootView):
    """
    Welcome to the ATMP API Root.
    Use the links below to explore available resources.
    - 🔐 Authentication
    -📄 Incident Reports
    - 📁 Document Management
    """


class CustomDefaultRouter(DefaultRouter):
    APIRootView = CustomAPIRootView


class ATMPIncidentViewSet(viewsets.ModelViewSet):
    """
    REST API endpoint for ATMP incidents.
    Only 'employee' users may create; everyone authenticated may list.
    """
    serializer_class = ATMPIncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsProvider()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ATMPIncident.objects.all()
        if user.role == 'employee':
            return ATMPIncident.objects.filter(provider=user)
        return ATMPIncident.objects.filter(safety_manager=user)

    def perform_create(self, serializer):
        # Automatically set the reporting user
        serializer.save(provider=self.request.user)


class ATMPDocumentViewSet(viewsets.ModelViewSet):
    """
    REST API endpoint for ATMP documents.
    Authenticated users can list/upload their own documents.
    """
    serializer_class = ATMPDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ATMPDocument.objects.all()
        return ATMPDocument.objects.filter(uploaded_by=user)

    def perform_create(self, serializer):
        # Automatically set the uploader
        serializer.save(uploaded_by=self.request.user)
