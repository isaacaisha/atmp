# /home/siisi/atmp/atmp_app/views.py

import logging
import json 
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404 
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Count, Q 


from .mixins import ProviderOrSuperuserMixin, EmployeeRequiredMixin, SafetyManagerMixin
from .models import (
    DossierATMP, DossierStatus, Contentieux, Document, Audit,
    AuditStatus, ContentieuxStatus, JuridictionStep, AuditDecision 
)
from .forms import (
    DossierATMPForm,
    ContentieuxForm, DocumentForm
)
from users.models import UserRole 

logger = logging.getLogger(__name__) 

# ---------------------- HTML Views (Django Templates) ----------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'atmp_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.role == UserRole.EMPLOYEE:
            ctx['incidents_count'] = DossierATMP.objects.filter(created_by=user).count()
            ctx['pending_incidents'] = DossierATMP.objects.filter(
                created_by=user,
                status=DossierStatus.A_ANALYSER
            ).count()
        elif user.role == UserRole.SAFETY_MANAGER:
            ctx['incidents_count'] = DossierATMP.objects.filter(safety_manager=user).count()
            ctx['pending_incidents'] = DossierATMP.objects.filter(
                safety_manager=user,
                status=DossierStatus.A_ANALYSER
            ).count()
        else:
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

    def form_invalid(self, form):
        logger.error(f"Form validation failed for IncidentCreateView:")
        logger.error(f"Main form errors: {form.errors.as_json()}")
        if hasattr(form, 'entreprise_form') and form.entreprise_form.errors:
            logger.error(f"Entreprise form errors: {form.entreprise_form.errors.as_json()}")
        if hasattr(form, 'salarie_form') and form.salarie_form.errors:
            logger.error(f"Salarie form errors: {form.salarie_form.errors.as_json()}")
        if hasattr(form, 'accident_form') and form.accident_form.errors:
            logger.error(f"Accident form errors: {form.accident_form.errors.as_json()}")

        messages.warning(self.request, "There was an error creating the incident. Please check the form for details.")
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form) 

        uploaded_file = form.cleaned_data.get('uploaded_file')
        document_type = form.cleaned_data.get('document_type')
        document_description = form.cleaned_data.get('document_description')

        if uploaded_file and document_type: 
            try:
                document = Document.objects.create(
                    uploaded_by=self.request.user,
                    document_type=document_type,
                    original_name=uploaded_file.name,
                    description=document_description,
                    file=uploaded_file, 
                    mime_type=uploaded_file.content_type,
                    size=uploaded_file.size,
                    contentieux=None 
                )
                self.object.documents.add(document) 
                logger.info(f"Document {document.pk} attached to incident {self.object.pk}")
                messages.success(self.request, f"Document '{document.original_name}' uploaded successfully!")
            except Exception as e:
                logger.error(f"Error creating/attaching document for incident {self.object.pk}: {e}", exc_info=True)
                messages.warning(self.request, "Incident created, but there was an issue uploading the document.")


        messages.success(self.request, "Incident created successfully!")
        return response


class IncidentListView(LoginRequiredMixin, ListView):
    model = DossierATMP
    template_name = 'atmp_app/incident_list.html'
    context_object_name = 'incidents'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        queryset = DossierATMP.objects.all().order_by('-created_at')
        if user.is_superuser:
            return queryset
        if user.role == UserRole.EMPLOYEE:
            return queryset.filter(created_by=user)
        if user.role == UserRole.SAFETY_MANAGER:
            return queryset.filter(safety_manager=user)
        return DossierATMP.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = DossierStatus.choices
        return context


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = DossierATMP
    template_name = 'atmp_app/incident_detail.html'
    context_object_name = 'incident'

    def get_queryset(self):
        # We need to *not* use select_related('tiers') here because it will cause an INNER JOIN
        # and fail if no tiers object exists. Instead, we'll access it directly in get_context_data
        # and handle the RelatedObjectDoesNotExist exception.
        qs = super().get_queryset().select_related(
            'safety_manager', 'created_by', 'contentieux', 'audit' # Removed 'tiers' from select_related
        ).prefetch_related(
            'documents', 'temoin_set', 'contentieux__documents', 'contentieux__juridiction_steps_set',
            'audit__checklist_items' 
        )
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(Q(created_by=user) | Q(safety_manager=user))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = self.get_object() 
        
        context['contentieux'] = incident.contentieux
        context['audit'] = incident.audit
        context['documents'] = incident.documents.all() 
        context['temoins'] = incident.temoin_set.all() 
        
        # Safely get the 'tiers' object using a try-except block
        try:
            context['tiers'] = incident.tiers
        except DossierATMP.tiers.RelatedObjectDoesNotExist: # <-- Specific exception for OneToOneField
            context['tiers'] = None # Assign None if no tiers object exists

        return context


class IncidentUpdateView(ProviderOrSuperuserMixin, UpdateView):
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
        
        uploaded_file = form.cleaned_data.get('uploaded_file')
        document_type = form.cleaned_data.get('document_type')
        document_description = form.cleaned_data.get('document_description')

        if uploaded_file and document_type:
            try:
                document = Document.objects.create(
                    uploaded_by=self.request.user,
                    document_type=document_type,
                    original_name=uploaded_file.name,
                    description=document_description,
                    file=uploaded_file,
                    mime_type=uploaded_file.content_type,
                    size=uploaded_file.size,
                    contentieux=None 
                )
                self.object.documents.add(document) 
                messages.success(self.request, f"New document '{document.original_name}' uploaded and linked.")
            except Exception as e:
                logger.error(f"Error creating/attaching document for incident {self.object.pk} during update: {e}", exc_info=True)
                messages.warning(self.request, "Incident updated, but there was an issue uploading the new document.")
        return response

    def get_queryset(self):
        user = self.request.user
        queryset = DossierATMP.objects.all()
        if not user.is_superuser:
            queryset = queryset.filter(Q(created_by=user) | Q(safety_manager=user))
        return queryset


class IncidentDeleteView(ProviderOrSuperuserMixin, DeleteView):
    model = DossierATMP
    template_name = 'atmp_app/incident_confirm_delete.html'
    success_url = reverse_lazy('atmp_app:incident-list')
    context_object_name = 'incident'

    def get_queryset(self):
        user = self.request.user
        queryset = DossierATMP.objects.all()
        if not user.is_superuser:
            queryset = queryset.filter(Q(created_by=user) | Q(safety_manager=user))
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Incident deleted successfully!")
        return super().delete(request, *args, **kwargs)


class ContentieuxCreateView(SafetyManagerMixin, CreateView):
    model = Contentieux
    form_class = ContentieuxForm
    template_name = 'atmp_app/contentieux_form.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            self.dossier = get_object_or_404(DossierATMP, pk=kwargs['dossier_pk'])
            if hasattr(self.dossier, 'contentieux') and self.dossier.contentieux:
                messages.warning(request, "A contentieux already exists for this dossier.")
                return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': self.dossier.pk}))
            
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            messages.warning(request, "Dossier not found.")
            return redirect(reverse('atmp_app:dashboard'))
        except PermissionDenied: 
            messages.error(request, "You do not have permission to create contentieux for this dossier.")
            return redirect(reverse('atmp_app:dashboard'))
        except Exception as e:
            logger.exception(f"Error in ContentieuxCreateView dispatch: {e}")
            messages.error(request, "An unexpected error occurred.")
            return redirect(reverse('atmp_app:dashboard'))

    def get_initial(self):
        initial = super().get_initial()
        initial['dossier_atmp'] = self.dossier
        initial['subject'] = json.dumps({"title": f"Contentieux for {self.dossier.reference}", "description": f"Contentieux initiated for incident {self.dossier.reference}."}, indent=2)
        initial['status'] = ContentieuxStatus.DRAFT.value
        initial['juridiction_steps'] = json.dumps({}) 
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dossier_pk'] = self.dossier.pk 
        return context

    def form_valid(self, form):
        form.instance.dossier_atmp = self.dossier
        response = super().form_valid(form)
        messages.success(self.request, "Contentieux created successfully!")
        
        self.dossier.status = DossierStatus.TRANSFORME_EN_CONTENTIEUX.value
        self.dossier.save()

        return response

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.dossier.pk})


class JuridiqueDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_juridique.html'
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == UserRole.JURIST

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_contentieux'] = Contentieux.objects.count()
        context['contentieux_by_status'] = Contentieux.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        context['total_juridiction_steps'] = JuridictionStep.objects.count()
        context['steps_by_juridiction'] = JuridictionStep.objects.values('juridiction').annotate(count=Count('id')).order_by('juridiction')
        context['steps_by_decision'] = JuridictionStep.objects.values('decision').annotate(count=Count('id')).order_by('decision')

        context['pending_contentieux'] = Contentieux.objects.filter(
            status=ContentieuxStatus.EN_COURS
        ).count()
        
        context['recent_contentieux'] = Contentieux.objects.order_by('-created_at')[:5]
        
        return context


class RHDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_rh.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == UserRole.RH

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_incidents'] = DossierATMP.objects.count()
        context['incidents_by_status'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        context['incidents_by_creator_role'] = DossierATMP.objects.values('created_by__role').annotate(count=Count('id')).order_by('created_by__role')

        context['incidents_a_analyser_count'] = DossierATMP.objects.filter(
            status=DossierStatus.A_ANALYSER
        ).count()
        context['incidents_en_analyse_count'] = DossierATMP.objects.filter(
            status=DossierStatus.ANALYSE_EN_COURS
        ).count()

        context['incidents_by_safety_manager'] = DossierATMP.objects.values('safety_manager__email').annotate(count=Count('id')).order_by('-count')

        return context


class QSEDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_qse.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == UserRole.QSE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_incidents'] = DossierATMP.objects.count()
        context['incidents_by_status'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        context['incidents_by_location'] = DossierATMP.objects.values('location').annotate(count=Count('id')).order_by('-count')
        
        context['total_audits'] = Audit.objects.count()
        context['audits_by_status'] = Audit.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['audits_by_decision'] = Audit.objects.values('decision').annotate(count=Count('id')).order_by('decision')
        
        context['contestation_recommended_incidents'] = DossierATMP.objects.filter(
            audit__decision=AuditDecision.CONTEST
        ).count()
        
        context['audits_in_progress'] = Audit.objects.filter(status=AuditStatus.IN_PROGRESS).count()

        return context


class DirectionDashboardHTMLView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'atmp_app/dashboard_direction.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == UserRole.DIRECTION

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_dossiers'] = DossierATMP.objects.count()
        context['total_contentieux'] = Contentieux.objects.count()
        context['total_audits'] = Audit.objects.count()
        
        context['dossiers_status_summary'] = DossierATMP.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['contentieux_status_summary'] = Contentieux.objects.values('status').annotate(count=Count('id')).order_by('status')
        context['audits_status_summary'] = Audit.objects.values('status').annotate(count=Count('id')).order_by('status')
        
        context['contentieux_from_contested_dossiers'] = Contentieux.objects.filter(
            dossier_atmp__audit__decision=AuditDecision.CONTEST
        ).count()
        context['contentieux_from_not_contested_dossiers'] = Contentieux.objects.filter(
            dossier_atmp__audit__decision=AuditDecision.DO_NOT_CONTEST
        ).count()
        
        context['dossiers_by_safety_manager'] = DossierATMP.objects.values('safety_manager__email').annotate(count=Count('id')).order_by('-count')

        return context


class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'atmp_app/document_upload.html' 

    def dispatch(self, request, *args, **kwargs):
        self.incident = get_object_or_404(DossierATMP, pk=kwargs['incident_pk'])
        
        user = request.user
        if not (user.is_superuser or user.id == self.incident.created_by_id or user.id == self.incident.safety_manager_id):
            messages.warning(request, "You do not have permission to upload documents for this incident.")
            return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': self.incident.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'contentieux': None}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident_pk'] = self.incident.pk 
        context['documents'] = self.incident.documents.all() 
        return context

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        
        contentieux_instance = None
        try:
            contentieux_instance = self.incident.contentieux 
        except Contentieux.DoesNotExist:
            pass 

        if contentieux_instance:
            form.instance.contentieux = contentieux_instance

        uploaded_file = self.request.FILES.get('file')
        if uploaded_file:
            form.instance.original_name = uploaded_file.name
            form.instance.mime_type = uploaded_file.content_type
            form.instance.size = uploaded_file.size
        else:
            messages.warning(self.request, "No file uploaded.")
            return self.form_invalid(form)

        response = super().form_valid(form) 
        
        self.incident.documents.add(self.object)

        messages.success(self.request, "Document uploaded successfully!")
        return response

    def get_success_url(self):
        return reverse('atmp_app:incident-detail', kwargs={'pk': self.incident.pk})
