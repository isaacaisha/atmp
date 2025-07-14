# /home/siisi/atmp/atmp_app/urls.py

from django.urls import path, include, reverse
from django.views.generic import RedirectView

from .views import (
    DashboardView,
    IncidentCreateView,
    IncidentListView,
    IncidentDetailView,
    IncidentUpdateView,
    IncidentDeleteView,
)

app_name = 'atmp_app'

urlpatterns = [
    # Redirect root of this app to dashboard
    path('', RedirectView.as_view(pattern_name='atmp_app:dashboard', permanent=False)),

    path('dashboard/',                 DashboardView.as_view(),      name='dashboard'),
    path('incidents/create/',          IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/',                 IncidentListView.as_view(),   name='incident-list'),
    path('incidents/<int:pk>/',        IncidentDetailView.as_view(), name='incident-detail'),
    path('incidents/<int:pk>/edit/',   IncidentUpdateView.as_view(), name='incident-update'),
    path('incidents/<int:pk>/delete/', IncidentDeleteView.as_view(), name='incident-delete'),
]
