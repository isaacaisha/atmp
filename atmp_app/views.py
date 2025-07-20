# /home/siisi/atmp/atmp_app/views.py

import logging
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect # Added redirect
from django.http import Http404, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Count, Q # Added Q for complex queries


from .mixins import ProviderOrSuperuserMixin, EmployeeRequiredMixin, SafetyManagerMixin # Assuming these are defined elsewhere
from .models import (
    DossierATMP, DossierStatus, Contentieux, Document, Audit,
    AuditStatus, ContentieuxStatus, JuridictionStep, AuditDecision # Added AuditDecision
)
from .forms import (
    DossierATMPForm, SafetyManagerChoiceField, # SafetyManagerChoiceField might be unused now.
    ContentieuxForm, DocumentForm
)

logger = logging.getLogger(__name__) # Initialize logger

# ---------------------- HTML Views (Django Templates) ----------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Simple dashboard/home view for logged-in users.
    """
    template_name = 'atmp_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Corrected 'provider' to 'created_by' for employee incidents
        if user.role == 'employee':
            ctx['incidents_count'] = DossierATMP.objects.filter(created_by=user).count()
            ctx['pending_incidents'] = DossierATMP.objects.filter(
                created_by=user,
                status=DossierStatus.A_ANALYSER
            ).count()
        elif user.role == 'safety_manager':
            ctx['incidents_count'] = DossierATMP.objects.filter(safety_manager=user).count()
            ctx['pending_incidents'] = DossierATMP.objects.filter(
                safety_manager=user,
                status=DossierStatus.A_ANALYSER
            ).count()
        else:  # admin or other roles (like juridique, rh, qse, direction)
            ctx['incidents_count'] = DossierATMP.objects.count()
            ctx['pending_incidents'] = DossierATMP.objects.filter(
                status=DossierStatus.A_ANALYSER
            ).count()
            
        ctx['contentieux_count'] = Contentieux.objects.count()
        ctx['audits_count'] = Audit.objects.count()
        
        return ctx


class IncidentCreateView(ProviderOrSuperuserMixin, CreateView):
    model = DossierATMP
    form_class = DossierATMPForm
    template_name = 'atmp_app/incident_form.html'
    success_url = reverse_lazy('atmp_app:incident-list')

    # Add this method back!
    def form_invalid(self, form):
        logger.error(f"Form validation failed for IncidentCreateView:")
        logger.error(f"Main form errors: {form.errors}")
        if hasattr(form, 'entreprise_form'):
            logger.error(f"Entreprise form errors: {form.entreprise_form.errors}")
        if hasattr(form, 'salarie_form'):
            logger.error(f"Salarie form errors: {form.salarie_form.errors}")
        if hasattr(form, 'accident_form'):
            logger.error(f"Accident form errors: {form.accident_form.errors}")

        messages.warning(self.request, "There was an error creating the incident. Please check the form for details.")
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # It's here that the form's clean method (including sub-forms) has already run
        # and populated form.cleaned_data['entreprise'], etc.
        response = super().form_valid(form) # This saves the DossierATMP instance

        # Get the uploaded file and its metadata from the form
        uploaded_file = form.cleaned_data.get('uploaded_file')
        document_type = form.cleaned_data.get('document_type')
        document_description = form.cleaned_data.get('document_description')

        if uploaded_file and document_type: # Only proceed if both file and type are provided
            try:
                document = Document.objects.create(
                    uploaded_by=self.request.user,
                    document_type=document_type,
                    original_name=uploaded_file.name,
                    description=document_description,
                    file=uploaded_file, # Django's FileField handles saving the file
                    mime_type=uploaded_file.content_type,
                    size=uploaded_file.size,
                    contentieux=None # Set to None initially as Contentieux might not exist yet
                )
                # Link the document to the DossierATMP's ManyToMany field
                self.object.documents.add(document) # `self.object` is the newly created DossierATMP
                logger.info(f"Document {document.pk} attached to incident {self.object.pk}")
            except Exception as e:
                logger.error(f"Error creating/attaching document for incident {self.object.pk}: {e}", exc_info=True)
                messages.warning(self.request, "Incident created, but there was an issue uploading the document.")


        messages.success(self.request, "Incident created successfully!")
        return response


class IncidentListView(LoginRequiredMixin, ListView):
    """
    HTML View: List all incidents for the logged-in user.
    Employees see their own reports; safety managers see incidents assigned to them.
    """
    model = DossierATMP
    template_name = 'atmp_app/incident_list.html'
    context_object_name = 'incidents'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DossierATMP.objects.all().order_by('-created_at')
        if user.role == 'employee':
            return DossierATMP.objects.filter(created_by=user).order_by('-created_at') # Corrected 'provider' to 'created_by'
        return DossierATMP.objects.filter(safety_manager=user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = DossierStatus.choices
        return context


class IncidentDetailView(LoginRequiredMixin, DetailView):
    """
    HTML View: Show all details for a single incident.
    """
    model = DossierATMP
    template_name = 'atmp_app/incident_detail.html'
    context_object_name = 'incident'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = self.get_object()
        
        # Add related contentieux if exists
        try:
            context['contentieux'] = incident.contentieux
        except Contentieux.DoesNotExist:
            context['contentieux'] = None
            
        # Add related audit if exists
        try:
            context['audit'] = incident.audit
        except Audit.DoesNotExist:
            context['audit'] = None
            
        # Add documents
        context['documents'] = incident.documents.all()
        
        return context


class IncidentUpdateView(ProviderOrSuperuserMixin, UpdateView):
    """
    HTML View: Allow users to update incidents based on their role.
    """
    model = DossierATMP
    form_class = DossierATMPForm
    template_name = 'atmp_app/incident_form.html'
    context_object_name = 'incident'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Incident updated successfully!")
        # Document handling: See comments in IncidentCreateView.
        # document = form.cleaned_data.get('document')
        # if document:
        #     Document.objects.create( # Changed ATMPDocument to Document
        #         incident=self.object, # incident changed to dossier_atmp if Document had that field
        #         uploaded_by=self.request.user,
        #         file=document,
        #     )
        return response

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DossierATMP.objects.all()
        if user.role == 'employee':
            return DossierATMP.objects.filter(created_by=user) # Corrected 'provider' to 'created_by'
        return DossierATMP.objects.filter(safety_manager=user)


class IncidentDeleteView(ProviderOrSuperuserMixin, DeleteView):
    """
    HTML View: Allow users to delete incidents based on their role.
    """
    model = DossierATMP
    template_name = 'atmp_app/incident_confirm_delete.html'
    success_url = reverse_lazy('atmp_app:incident-list')
    context_object_name = 'incident'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DossierATMP.objects.all()
        if user.role == 'employee':
            return DossierATMP.objects.filter(created_by=user) # Corrected 'provider' to 'created_by'
        return DossierATMP.objects.filter(safety_manager=user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Incident deleted successfully!")
        return super().delete(request, *args, **kwargs)


class ContentieuxCreateView(SafetyManagerMixin, CreateView):
    """
    View to create a new contentieux from an ATMP dossier
    """
    model = Contentieux
    form_class = ContentieuxForm
    template_name = 'atmp_app/contentieux_form.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            # Check if dossier exists first
            self.dossier = get_object_or_404(DossierATMP, pk=kwargs['dossier_pk'])
            # Check if a contentieux already exists for this dossier
            if hasattr(self.dossier, 'contentieux') and self.dossier.contentieux:
                messages.warning(request, "A contentieux already exists for this dossier.")
                return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': self.dossier.pk}))
            # Check permissions if needed
            if not request.user.has_perm('atmp_app.add_contentieux'): # Requires 'atmp_app.add_contentieux' permission
                raise PermissionDenied
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            messages.warning(request, "Dossier not found.")
            return redirect(reverse('atmp_app:dashboard'))
        except PermissionDenied:
            messages.warning(request, "You do not have permission to create contentieux.")
            return redirect(reverse('atmp_app:dashboard'))

    def get_initial(self):
        initial = super().get_initial()
        # Pre-populate reference or other fields from dossier if needed
        initial['dossier_atmp'] = self.dossier
        # You might want to generate a default reference here
        # initial['reference'] = f"CONT-{self.dossier.reference}"
        return initial

    def form_valid(self, form):
        form.instance.dossier_atmp = self.dossier
        # If your Contentieux model has a 'created_by' field, set it here
        # form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Contentieux created successfully!")
        return response

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.dossier.pk})


class JuridiqueDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_juridique.html' # Create this template
    
    def test_func(self):
        # Only allow users with 'juridique' role or superusers
        return self.request.user.is_superuser or self.request.user.role == 'juridique'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Contentieux Overview
        context['total_contentieux'] = Contentieux.objects.count()
        context['contentieux_by_status'] = Contentieux.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        # Juridiction Steps Overview
        context['total_juridiction_steps'] = JuridictionStep.objects.count()
        context['steps_by_juridiction'] = JuridictionStep.objects.values('juridiction').annotate(count=Count('id')).order_by('juridiction')
        context['steps_by_decision'] = JuridictionStep.objects.values('decision').annotate(count=Count('id')).order_by('decision')

        # Contentieux requiring attention (e.g., in progress)
        context['pending_contentieux'] = Contentieux.objects.filter(
            status=ContentieuxStatus.EN_COURS
        ).count()
        
        # Example: Recent contentieux
        context['recent_contentieux'] = Contentieux.objects.order_by('-created_at')[:5]
        
        return context


class RHDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_rh.html' # Create this template

    def test_func(self):
        # Only allow users with 'rh' role or superusers
        return self.request.user.is_superuser or self.request.user.role == 'rh'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Incidents Overview relevant to HR
        context['total_incidents'] = DossierATMP.objects.count()
        context['incidents_by_status'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        # Incidents by creator role (assuming 'employee' role for most creators)
        context['incidents_by_creator_role'] = DossierATMP.objects.values('created_by__role').annotate(count=Count('id')).order_by('created_by__role')

        # Incidents requiring HR follow-up (e.g., pending analysis, or specific statuses)
        context['incidents_a_analyser_count'] = DossierATMP.objects.filter(
            status=DossierStatus.A_ANALYSER
        ).count()
        context['incidents_en_analyse_count'] = DossierATMP.objects.filter(
            status=DossierStatus.ANALYSE_EN_COURS
        ).count()

        # You might also want to show:
        # - Incidents by safety manager assigned
        context['incidents_by_safety_manager'] = DossierATMP.objects.values('safety_manager__email').annotate(count=Count('id')).order_by('-count')

        return context


class QSEDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_qse.html' # Create this template

    def test_func(self):
        # Only allow users with 'qse' role or superusers
        return self.request.user.is_superuser or self.request.user.role == 'qse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Incident Statistics relevant to QSE
        context['total_incidents'] = DossierATMP.objects.count()
        context['incidents_by_status'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        # Incidents by location
        context['incidents_by_location'] = DossierATMP.objects.values('location').annotate(count=Count('id')).order_by('-count')
        
        # Audit Statistics
        context['total_audits'] = Audit.objects.count()
        context['audits_by_status'] = Audit.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['audits_by_decision'] = Audit.objects.values('decision').annotate(count=Count('id')).order_by('decision')
        
        # Incidents that were contested based on audit decision
        context['contestation_recommended_incidents'] = DossierATMP.objects.filter(
            audit__decision=AuditDecision.CONTEST
        ).count()
        
        # Audits in progress
        context['audits_in_progress'] = Audit.objects.filter(status=AuditStatus.IN_PROGRESS).count()

        return context


class DirectionDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_direction.html' # Create this template

    def test_func(self):
        # Only allow users with 'direction' role or superusers
        return self.request.user.is_superuser or self.request.user.role == 'direction'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Overall Summary
        context['total_dossiers'] = DossierATMP.objects.count()
        context['total_contentieux'] = Contentieux.objects.count()
        context['total_audits'] = Audit.objects.count()
        
        # High-level status breakdowns
        context['dossiers_status_summary'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['contentieux_status_summary'] = Contentieux.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['audits_status_summary'] = Audit.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        # Key performance indicators (KPIs) - example: contested vs. non-contested cases (derived from audit)
        context['contentieux_from_contested_dossiers'] = Contentieux.objects.filter(
            dossier_atmp__audit__decision=AuditDecision.CONTEST
        ).count()
        context['contentieux_from_not_contested_dossiers'] = Contentieux.objects.filter(
            dossier_atmp__audit__decision=AuditDecision.DO_NOT_CONTEST
        ).count()
        
        # Example of data by safety manager
        context['dossiers_by_safety_manager'] = DossierATMP.objects.values('safety_manager__email').annotate(count=Count('id')).order_by('-count')

        return context


class DocumentUploadView(LoginRequiredMixin, CreateView):
    """
    View to upload a document for a specific incident.
    """
    model = Document
    form_class = DocumentForm
    template_name = 'atmp_app/document_upload_form.html' # You'll need to create this template

    def dispatch(self, request, *args, **kwargs):
        # Ensure the incident exists
        self.incident = get_object_or_404(DossierATMP, pk=kwargs['incident_pk'])
        # Add any permission checks here if needed (e.g., only safety manager or creator)
        if not (request.user.is_superuser or request.user.id == self.incident.created_by_id or request.user.id == self.incident.safety_manager_id):
            messages.warning(request, "You do not have permission to upload documents for this incident.")
            return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': self.incident.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the incident to the form if needed for validation/initial data
        kwargs['initial'] = {'contentieux': None} # Ensure contentieux is not pre-set if it's optional
        return kwargs

    #def form_valid(self, form):
    #    form.instance.uploaded_by = self.request.user
    #    
    #    # The Document model currently has a ForeignKey to Contentieux (not nullable).
    #    # If this document is for an incident, it needs to be linked to the incident's contentieux.
    #    # If no contentieux exists for the incident, this operation would fail unless Document.contentieux is nullable.
    #    # Assuming Document.contentieux is NOT nullable as per your model definition.
    #    
    #    contentieux_instance = None
    #    try:
    #        contentieux_instance = self.incident.contentieux
    #    except Contentieux.DoesNotExist:
    #        pass # No contentieux yet, we need to handle this.
#
    #    if contentieux_instance:
    #        form.instance.contentieux = contentieux_instance
    #    else:
    #        # If Contentieux is a required field on Document, and no contentieux exists for the incident,
    #        # we cannot save the document unless Document.contentieux is made nullable in models.py
    #        # or you enforce contentieux creation before document upload for incidents.
    #        messages.error(self.request, "A contentieux must exist for this incident to link documents. Please create one first.")
    #        return self.form_invalid(form) # Rerender form with errors or redirect
#
    #    # Handle file details (original_name, mime_type, size)
    #    # Ensure your DocumentForm handles `file` field
    #    uploaded_file = self.request.FILES.get('file') # Assuming the form field is named 'file'
    #    if uploaded_file:
    #        form.instance.original_name = uploaded_file.name
    #        form.instance.mime_type = uploaded_file.content_type
    #        form.instance.size = uploaded_file.size
    #    else:
    #        messages.error(self.request, "No file uploaded.")
    #        return self.form_invalid(form)
#
#
    #    response = super().form_valid(form)
    #    
    #    # After saving the Document instance, link it to the DossierATMP's ManyToMany field
    #    # because DossierATMP also has a 'documents' M2M.
    #    self.incident.documents.add(self.object) # `self.object` is the newly created Document instance
    #    
    #    messages.success(self.request, "Document uploaded successfully!")
    #    return response

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        # Link the document to the incident first
        form.instance.dossier_atmp = self.incident # Assuming a ForeignKey to DossierATMP is added to Document, or handled via M2M add below.

        contentieux_instance = None
        try:
            contentieux_instance = self.incident.contentieux
        except Contentieux.DoesNotExist:
            pass

        if contentieux_instance:
            form.instance.contentieux = contentieux_instance
        # ELSE: If contentieux is nullable, it's okay to save without one.
        # If it's not nullable, the error message/redirect logic is still valid.

        # Handle file details (original_name, mime_type, size)
        uploaded_file = self.request.FILES.get('file')
        if uploaded_file:
            form.instance.original_name = uploaded_file.name
            form.instance.mime_type = uploaded_file.content_type
            form.instance.size = uploaded_file.size
        else:
            messages.warning(self.request, "No file uploaded.")
            return self.form_invalid(form)

        response = super().form_valid(form)

        # Link the document to the DossierATMP's ManyToMany field
        self.incident.documents.add(self.object)

        messages.success(self.request, "Document uploaded successfully!")
        return response

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.incident.pk})
        