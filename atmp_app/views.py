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
from django.forms import inlineformset_factory


from .mixins import ProviderOrSuperuserMixin, EmployeeRequiredMixin, SafetyManagerMixin
from .models import (
    DossierATMP, DossierStatus, Contentieux, Document, Audit, AuditStatus,
    ContentieuxStatus, JuridictionStep, AuditDecision, Temoin
)
from .forms import (
    DossierATMPForm, TemoinForm,
    ContentieuxForm, DocumentForm, ProfileEditForm
)
from users.models import CustomUser, UserRole
from django_otp.plugins.otp_totp.models import TOTPDevice

logger = logging.getLogger(__name__) 

# Define the TemoinFormSet
TemoinFormSet = inlineformset_factory(
    DossierATMP,  # Parent model
    Temoin,       # Child model
    form=TemoinForm, # The form to use for each Temoin instance
    extra=1,      # Number of empty forms to display
    can_delete=True, # Allow deleting existing Temoin instances
    can_order=False, # Whether to allow reordering (usually not needed)
    min_num=0,    # Minimum number of forms that must be filled out
    max_num=5,    # Maximum number of forms allowed (optional)
)

# ---------------------- HTML Views (Django Templates) ----------------------

class DashboardView(TemplateView):
    template_name = 'atmp_app/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user # user will be an AnonymousUser object if not logged in
        
        # You might want to adjust logic inside here if specific data should only
        # appear for authenticated users, e.g., using `if user.is_authenticated:`
        if user.is_authenticated:
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
            else: # Admin or Superuser for authenticated users
                ctx['incidents_count'] = DossierATMP.objects.count()
                ctx['pending_incidents'] = DossierATMP.objects.filter(
                    status=DossierStatus.A_ANALYSER
                ).count()
            
            ctx['contentieux_count'] = Contentieux.objects.count()
            ctx['audits_count'] = Audit.objects.count()
        else:
            # Optionally, set default or empty values for non-authenticated users
            ctx['incidents_count'] = None
            ctx['pending_incidents'] = None
            ctx['contentieux_count'] = None
            ctx['audits_count'] = None
            
        return ctx


class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser # The user model
    form_class = ProfileEditForm # The form for editing the profile
    template_name = 'atmp_app/profile.html' # The template to render
    context_object_name = 'user_profile' # The name of the user object in the template context

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.
        In this case, it's always the currently logged-in user.
        """
        return self.request.user

    def get_success_url(self):
        """
        Redirects to the profile page itself after a successful update.
        """
        messages.success(self.request, "Your profile has been updated successfully!")
        return reverse_lazy('atmp_app:profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add additional context specific to the profile page
        context['has_2fa'] = TOTPDevice.objects.filter(user=self.request.user, confirmed=True).exists()
        # You might also want a link to change password
        context['password_change_url'] = reverse_lazy('password_change') # Assuming you have a password change URL in your main urls.py or auth URLs
        return context

    def form_valid(self, form):
        # The form.save() method will correctly update the self.object (which is request.user)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class IncidentCreateView(ProviderOrSuperuserMixin, CreateView):
    model = DossierATMP
    form_class = DossierATMPForm
    template_name = 'atmp_app/incident_form.html'
    success_url = reverse_lazy('atmp_app:incident-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Main form is already in context as 'form'
        context['entreprise_form'] = context['form'].entreprise_form
        context['salarie_form'] = context['form'].salarie_form
        context['accident_form'] = context['form'].accident_form
        context['tiers_implique_form'] = context['form'].tiers_implique_form

        # Initialize Temoin formset for GET (no data, new object) or POST (with submitted data)
        # Note: self.object is not yet set for CreateView on initial GET, so instance=None is implied.
        if self.request.POST:
            context['temoin_formset'] = TemoinFormSet(self.request.POST) # No instance yet for new creation
        else:
            context['temoin_formset'] = TemoinFormSet() # No instance for a new empty formset
        return context

    def form_valid(self, form):
        # 1. Save the main form instance WITHOUT committing to the database yet.
        # This is CRUCIAL because the formset needs the parent object's PK.
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user # Assign created_by

        # 2. Instantiate the formset with POST data and the (unsaved) parent instance
        temoin_formset = TemoinFormSet(self.request.POST, instance=self.object)

        # 3. Perform combined validation: main form AND formset
        if form.is_valid() and temoin_formset.is_valid():
            # 4. Save the parent object to the database (it now gets its PK)
            self.object.save()

            # 5. Save the formset (it will use self.object.pk to link children)
            temoin_formset.save()

            # 6. Handle document upload (this logic remains largely the same, but occurs after main save)
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
                        contentieux=None # No contentieux linked at this stage for incident documents
                    )
                    self.object.documents.add(document)
                    logger.info(f"Document {document.pk} attached to incident {self.object.pk}")
                    messages.success(self.request, f"Document '{document.original_name}' uploaded successfully!")
                except Exception as e:
                    logger.error(f"Error creating/attaching document for incident {self.object.pk}: {e}", exc_info=True)
                    messages.warning(self.request, "Incident created, but there was an issue uploading the document.")

            messages.success(self.request, "Incident created successfully!")
            return redirect(self.get_success_url())
        else:
            # If validation fails for either main form or formset, re-render with errors.
            # get_context_data will be called again, which will re-initialize the formset
            # with self.request.POST data, so errors will be displayed.
            logger.error(f"Form or formset validation failed for IncidentCreateView.")
            logger.error(f"Main form errors: {form.errors.as_json()}")
            if hasattr(form, 'entreprise_form') and form.entreprise_form.errors:
                logger.error(f"Entreprise form errors: {form.entreprise_form.errors.as_json()}")
            if hasattr(form, 'salarie_form') and form.salarie_form.errors:
                logger.error(f"Salarie form errors: {form.salarie_form.errors.as_json()}")
            if hasattr(form, 'accident_form') and form.accident_form.errors:
                logger.error(f"Accident form errors: {form.accident_form.errors.as_json()}")
            if hasattr(form, 'tiers_implique_form') and form.tiers_implique_form.errors:
                logger.error(f"Tiers Implique form errors: {form.tiers_implique_form.errors.as_json()}")
            logger.error(f"Temoin formset errors: {temoin_formset.errors}") # Log formset errors

            messages.warning(self.request, "There was an error creating the incident. Please check the form for details.")
            # Important: Instead of super().form_invalid(form), manually render context.
            # This ensures temoin_formset (with its errors) is passed correctly.
            context = self.get_context_data(form=form) # Get context, which re-creates formset with POST data
            context['temoin_formset'] = temoin_formset # Ensure the specific formset instance (with errors) is passed
            return self.render_to_response(context)


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
        qs = super().get_queryset().select_related(
            'safety_manager', 'created_by', 'contentieux', 'audit'
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
        
        # Safely get the 'contentieux' object
        try:
            context['contentieux'] = incident.contentieux
        except DossierATMP.contentieux.RelatedObjectDoesNotExist:
            context['contentieux'] = None # Assign None if no contentieux object exists

        # Safely get the 'audit' object
        try:
            context['audit'] = incident.audit
        except DossierATMP.audit.RelatedObjectDoesNotExist:
            context['audit'] = None # Assign None if no audit object exists

        context['documents'] = incident.documents.all() 
        context['temoins'] = incident.temoin_set.all() 
        
        # This part was already correct for 'tiers'
        try:
            context['tiers'] = incident.tiers
        except DossierATMP.tiers.RelatedObjectDoesNotExist: 
            context['tiers'] = None 

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Main form is already in context as 'form'
        context['entreprise_form'] = context['form'].entreprise_form
        context['salarie_form'] = context['form'].salarie_form
        context['accident_form'] = context['form'].accident_form
        context['tiers_implique_form'] = context['form'].tiers_implique_form

        # Initialize Temoin formset for GET (existing object) or POST (with submitted data)
        if self.request.POST:
            context['temoin_formset'] = TemoinFormSet(self.request.POST, instance=self.object)
        else:
            context['temoin_formset'] = TemoinFormSet(instance=self.object) # Load existing witnesses
        return context

    def form_valid(self, form):
        # self.object is already loaded by UpdateView for existing instance
        # 1. Save the main form instance WITHOUT committing to the database yet.
        # This updates self.object but doesn't save it to DB until formset is ready.
        self.object = form.save(commit=False)

        # 2. Instantiate the formset with POST data and the parent instance
        temoin_formset = TemoinFormSet(self.request.POST, instance=self.object)

        # 3. Perform combined validation: main form AND formset
        if form.is_valid() and temoin_formset.is_valid():
            # 4. Save the parent object to the database
            self.object.save()

            # 5. Save the formset (it will use self.object.pk to link children)
            temoin_formset.save()

            messages.success(self.request, "Incident updated successfully!")

            # 6. Handle document upload (this logic remains largely the same)
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
                        contentieux=None # No contentieux linked at this stage for incident documents
                    )
                    self.object.documents.add(document)
                    messages.success(self.request, f"New document '{document.original_name}' uploaded and linked.")
                except Exception as e:
                    logger.error(f"Error creating/attaching document for incident {self.object.pk} during update: {e}", exc_info=True)
                    messages.warning(self.request, "Incident updated, but there was an issue uploading the new document.")
            
            return redirect(self.get_success_url())
        else:
            # If validation fails for either main form or formset, re-render with errors.
            logger.error(f"Form or formset validation failed for IncidentUpdateView.")
            logger.error(f"Main form errors: {form.errors.as_json()}")
            if hasattr(form, 'entreprise_form') and form.entreprise_form.errors:
                logger.error(f"Entreprise form errors: {form.entreprise_form.errors.as_json()}")
            if hasattr(form, 'salarie_form') and form.salarie_form.errors:
                logger.error(f"Salarie form errors: {form.salarie_form.errors.as_json()}")
            if hasattr(form, 'accident_form') and form.accident_form.errors:
                logger.error(f"Accident form errors: {form.accident_form.errors.as_json()}")
            if hasattr(form, 'tiers_implique_form') and form.tiers_implique_form.errors:
                logger.error(f"Tiers Implique form errors: {form.tiers_implique_form.errors.as_json()}")
            logger.error(f"Temoin formset errors: {temoin_formset.errors}") # Log formset errors

            messages.warning(self.request, "Veuillez corriger les erreurs dans le formulaire.")
            # Important: Manually render context to ensure temoin_formset (with its errors) is passed
            context = self.get_context_data(form=form)
            context['temoin_formset'] = temoin_formset # Ensure the specific formset instance (with errors) is passed
            return self.render_to_response(context)

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
        initial['dossier_atmp'] = self.dossier.pk # Pass the primary key, not the object directly
        # Pre-populate JSONFields as strings for the Textarea widgets
        initial['subject'] = json.dumps({"title": f"Contentieux for {self.dossier.reference}", "description": f"Contentieux initiated for incident {self.dossier.reference}."}, indent=2)
        initial['status'] = ContentieuxStatus.DRAFT.value
        initial['juridiction_steps'] = json.dumps({}) 
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure dossier_pk is passed for the cancel button URL
        context['dossier_pk'] = self.kwargs['dossier_pk'] # or self.dossier.pk if self.dossier is always set here
        return context

    def form_valid(self, form):
        # The dossier_atmp will be set correctly by the form's save method due to get_initial
        # The reference will be generated by Contentieux model's save method
        response = super().form_valid(form) # This calls form.save() which in turn calls model.save()
        messages.success(self.request, "Contentieux created successfully!")
        
        # Update dossier status
        self.dossier.status = DossierStatus.TRANSFORME_EN_CONTENTIEUX.value # Make sure DossierStatus is imported
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


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document

    def get_object(self, queryset=None):
        """
        Retrieve the document object to be deleted.
        """
        pk = self.kwargs.get(self.pk_url_kwarg)
        # Ensure the document exists
        document = get_object_or_404(self.model, pk=pk)
        return document

    def dispatch(self, request, *args, **kwargs):
        """
        Handles permission checks before accessing the view.
        """
        self.object = self.get_object() # Get the object first for permission checks

        # Permission check: Superuser OR the uploader
        if not (request.user.is_superuser or request.user == self.object.uploaded_by):
            messages.warning(request, "You do not have permission to delete this document.")
            # Determine where to redirect if permission is denied
            redirect_to_pk = self._get_incident_pk_for_redirect()
            if redirect_to_pk:
                return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': redirect_to_pk}))
            return redirect(request.META.get('HTTP_REFERER', reverse_lazy('atmp_app:dashboard'))) # Fallback

        # Only allow POST requests for deletion from the button/form
        if request.method == 'GET':
            # If a GET request somehow reaches here (e.g., direct URL access),
            # prevent deletion and redirect with a warning.
            messages.warning(request, "Direct access to delete page not allowed. Please use the delete button.")
            redirect_to_pk = self._get_incident_pk_for_redirect()
            if redirect_to_pk:
                return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': redirect_to_pk}))
            return redirect(request.META.get('HTTP_REFERER', reverse_lazy('atmp_app:dashboard')))

        return super().dispatch(request, *args, **kwargs)

    def _get_incident_pk_for_redirect(self):
        """
        Helper method to determine the DossierATMP (incident) PK for redirection.
        This handles documents directly linked to DossierATMP or via Contentieux.
        """
        # Prioritize linking via Contentieux if it exists and has a DossierATMP
        if self.object.contentieux and self.object.contentieux.dossier_atmp:
            return self.object.contentieux.dossier_atmp.pk
        # Otherwise, use the direct link to DossierATMP
        elif self.object.dossier_atmp:
            return self.object.dossier_atmp.pk
        return None

    def delete(self, request, *args, **kwargs):
        """
        Override the delete method to remove the file from storage
        before the database record is deleted.
        """
        # self.object is already set by dispatch
        # Get the incident PK for redirection *before* the document is deleted
        redirect_incident_pk = self._get_incident_pk_for_redirect()

        try:
            # Delete the actual file from storage first
            if self.object.file:
                self.object.file.delete(save=False) # save=False prevents saving the model after file deletion

            # Call the superclass delete method to delete the database record
            response = super().delete(request, *args, **kwargs)

            messages.success(request, f"Document '{self.object.original_name}' deleted successfully.")
            return response # This will use the success_url logic if defined, or redirect manually below

        except Exception as e:
            messages.warning(request, f"An error occurred while deleting the document: {e}")
            # If deletion fails, ensure we redirect back to the incident page
            if redirect_incident_pk:
                return redirect(reverse('atmp_app:incident-detail', kwargs={'pk': redirect_incident_pk}))
            return redirect(request.META.get('HTTP_REFERER', reverse_lazy('atmp_app:dashboard')))

    def get_success_url(self):
        """
        Defines the URL to redirect to after successful deletion.
        """
        return reverse_lazy('atmp_app:dashboard') # A safe fallback, but our delete method does explicit redirect
