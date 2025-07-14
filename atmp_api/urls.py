# /home/siisi/atmp/atmp_api/urls.py

from django.urls import path, include

from .auth_views import AuthViewSet

from .views import (
    CustomDefaultRouter,
    ATMPIncidentViewSet,
    ATMPDocumentViewSet,
)

app_name = 'atmp_api'

# 1) Create the router
router = CustomDefaultRouter()
router.register(r'auth',      AuthViewSet,          basename='auth')
router.register(r'incidents', ATMPIncidentViewSet,  basename='incident')
router.register(r'documents', ATMPDocumentViewSet,  basename='document')

urlpatterns = [
    # 2) API endpoints, all-in-one under /atmp/api/
    path('', include((router.urls, 'atmp_api'), namespace='api')),
]
