# /home/siisi/atmp/atmp_app/views.py

from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, ListView, DetailView, UpdateView, DeleteView

from .models import ATMPIncident, ATMPDocument
from .forms import IncidentForm


# ---------------------- HTML Views (Django Templates) ----------------------

class EmployeeRequiredMixin(UserPassesTestMixin):
    """Mixin to allow only employees (providers) to access certain views."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'employee'


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
            ctx['incidents_count'] = ATMPIncident.objects.filter(provider=user).count()
        else:
            ctx['incidents_count'] = 0
        return ctx


class IncidentCreateView(LoginRequiredMixin, EmployeeRequiredMixin, CreateView):
    """
    HTML View: Employee-only form to report a new ATMP incident.
    Automatically sets provider to the current user.
    """
    model = ATMPIncident
    form_class = IncidentForm
    template_name = 'atmp_app/incident_form.html'
    success_url = reverse_lazy('atmp_app:incident-list')

    def form_valid(self, form):
        form.instance.provider = self.request.user
        response = super().form_valid(form)
        document = form.cleaned_data.get('document')
        if document:
            ATMPDocument.objects.create(
                incident=self.object,
                uploaded_by=self.request.user,
                file=document,
            )
        return response


class IncidentListView(LoginRequiredMixin, ListView):
    """
    HTML View: List all incidents for the logged-in user.
    Employees see their own reports; safety managers see incidents assigned to them.
    """
    model = ATMPIncident
    template_name = 'atmp_app/incident_list.html'
    context_object_name = 'incidents'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ATMPIncident.objects.all()
        if user.role == 'employee':
            return ATMPIncident.objects.filter(provider=user)
        return ATMPIncident.objects.filter(safety_manager=user)


class IncidentDetailView(LoginRequiredMixin, DetailView):
    """
    HTML View: Show all details for a single incident.
    """
    model = ATMPIncident
    template_name = 'atmp_app/incident_detail.html'
    context_object_name = 'incident'


class IncidentUpdateView(LoginRequiredMixin, EmployeeRequiredMixin, UpdateView):
    """
    HTML View: Allow employees to update their own incidents.
    """
    model = ATMPIncident
    form_class = IncidentForm
    template_name = 'atmp_app/incident_form.html'
    context_object_name = 'incident'

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        document = form.cleaned_data.get('document')
        if document:
            ATMPDocument.objects.create(
                incident=self.object,
                uploaded_by=self.request.user,
                file=document,
            )
        return super().form_valid(form)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ATMPIncident.objects.all()
        return ATMPIncident.objects.filter(provider=user)


class IncidentDeleteView(LoginRequiredMixin, EmployeeRequiredMixin, DeleteView):
    """
    HTML View: Allow employees to delete their own incidents.
    """
    model = ATMPIncident
    template_name = 'atmp_app/incident_confirm_delete.html'
    success_url = reverse_lazy('atmp_app:incident-list')
    context_object_name = 'incident'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ATMPIncident.objects.all()
        return ATMPIncident.objects.filter(provider=user)
