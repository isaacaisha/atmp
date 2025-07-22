# /home/siisi/atmp/atmp_app/forms.py

import json
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _

from .models import (
    DossierATMP, Contentieux, Document, Temoin,
    DocumentType, DossierStatus, ContentieuxStatus,
    JuridictionType
)
from users.models import CustomUser, UserRole


User = get_user_model()


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email


class EntrepriseForm(forms.Form):
    name = forms.CharField(max_length=255, required=True,
                           widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(max_length=255, required=True,
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    siret = forms.CharField(max_length=14, required=True,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            help_text="14-digit SIRET number")


class SalarieForm(forms.Form):
    first_name = forms.CharField(max_length=100, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    social_security_number = forms.CharField(max_length=15, required=True,
                                              widget=forms.TextInput(attrs={'class': 'form-control'}),
                                              help_text="e.g., 179052A12345678")
    date_of_birth = forms.DateField(required=False,
                                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    job_title = forms.CharField(max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))


class AccidentForm(forms.Form):
    date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    time = forms.TimeField(required=True, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    description = forms.CharField(required=True,
                                  widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    type_of_accident = forms.CharField(max_length=255, required=False,
                                       widget=forms.TextInput(attrs={'class': 'form-control'}))
    detailed_circumstances = forms.CharField(required=True,
                                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class TiersImpliqueForm(forms.Form):
    # These fields match the expected keys within the 'tiers_implique' JSON data
    # We use _() for translation, as you imported gettext_lazy as _
    nom = forms.CharField(max_length=255, required=False, label=_("Nom du Tiers"),
                          widget=forms.TextInput(attrs={'class': 'form-control'}))
    adresse = forms.CharField(max_length=255, required=False, label=_("Adresse du Tiers"),
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    assurance = forms.CharField(max_length=255, required=False, label=_("Assurance"),
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    immatriculation = forms.CharField(max_length=255, required=False, label=_("Immatriculation"),
                                     widget=forms.TextInput(attrs={'class': 'form-control'}),
                                     help_text=_("e.g., vehicle registration"))


class DossierATMPForm(forms.ModelForm):
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role=UserRole.SAFETY_MANAGER),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_incident = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    uploaded_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    document_type = forms.ChoiceField(
        choices=DocumentType.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    document_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        initial_entreprise_data = self.instance.entreprise if self.instance and self.instance.entreprise else {}
        initial_salarie_data = self.instance.salarie if self.instance and self.instance.salarie else {}
        initial_accident_data = self.instance.accident if self.instance and self.instance.accident else {}
        initial_tiers_implique_data = self.instance.tiers_implique if self.instance and self.instance.tiers_implique else {}

        self.entreprise_form = EntrepriseForm(
            self.data if self.is_bound else None,
            prefix='entreprise',
            initial=initial_entreprise_data
        )
        self.salarie_form = SalarieForm(
            self.data if self.is_bound else None,
            prefix='salarie',
            initial=initial_salarie_data
        )
        self.accident_form = AccidentForm(
            self.data if self.is_bound else None,
            prefix='accident',
            initial=initial_accident_data
        )
        self.tiers_implique_form = TiersImpliqueForm(
            self.data if self.is_bound else None,
            prefix='tiers_implique',
            initial=initial_tiers_implique_data
        )

    class Meta:
        model = DossierATMP
        fields = [
            'reference',
            'safety_manager',
            'title',
            'description',
            'status',
            'date_of_incident',
            'location',
            'service_sante',
        ]
        widgets = {
            'reference':   forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'service_sante': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def is_valid(self):
        main_form_valid = super().is_valid()
        entreprise_form_valid = self.entreprise_form.is_valid()
        salarie_form_valid = self.salarie_form.is_valid()
        accident_form_valid = self.accident_form.is_valid()
        tiers_implique_form_valid = self.tiers_implique_form.is_valid()
        
        return main_form_valid and entreprise_form_valid and salarie_form_valid and accident_form_valid and tiers_implique_form_valid

    def clean(self):
        cleaned_data = super().clean()

        if self.entreprise_form.is_valid():
            cleaned_data['entreprise'] = self.entreprise_form.cleaned_data
        else:
            self.add_error(None, "Please correct errors in the Company Details section.")


        if self.salarie_form.is_valid():
            cleaned_data['salarie'] = self.salarie_form.cleaned_data
        else:
            self.add_error(None, "Please correct errors in the Employee Details section.")

        if self.accident_form.is_valid():
            cleaned_data['accident'] = self.accident_form.cleaned_data
        else:
            self.add_error(None, "Please correct errors in the Accident Details section.")

        if self.tiers_implique_form.is_valid():
            cleaned_data['tiers_implique'] = self.tiers_implique_form.cleaned_data
            if not any(value for value in cleaned_data['tiers_implique'].values()):
                cleaned_data['tiers_implique'] = None
        else:
            self.add_error(None, _("Please correct errors in the Tier Details section."))

        uploaded_file = cleaned_data.get('uploaded_file')
        document_type = cleaned_data.get('document_type')
        document_description = cleaned_data.get('document_description')

        if uploaded_file and not document_type:
            self.add_error('document_type', "Document type is required if a file is uploaded.")
        
        if not uploaded_file and not document_type and not document_description:
             pass

        return cleaned_data

    def clean_uploaded_file(self):
        file = self.cleaned_data.get('uploaded_file')
        if file:
            max_size = 10 * 1024 * 1024
            if file.size > max_size:
                raise ValidationError(f"File too large. Size should not exceed {max_size/1024/1024:.0f}MB.")
        return file


# --- NEW FORM FOR INDIVIDUAL JURIDICTION STEP ---
class JuridictionStepForm(forms.Form): # This is a regular forms.Form, not ModelForm
    step_type = forms.ChoiceField(
        choices=JuridictionType.choices, # Using the Enum from models.py
        label=_("Type of Jurisdiction"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    step_date = forms.DateField(
        label=_("Date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    step_notes = forms.CharField(
        label=_("Notes"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


# --- CONTENTIEUX FORM REDESIGN ---
class ContentieuxForm(forms.ModelForm):
    # New fields for subject, replacing the direct JSONField
    subject_title = forms.CharField(
        max_length=255,
        label=_("Subject Title"),
        help_text=_("A brief title for the contentieux subject."),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    subject_description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label=_("Subject Description"),
        help_text=_("Detailed description of the contentieux subject."),
        required=False
    )

    class Meta:
        model = Contentieux
        # EXCLUDE the original JSONFields from the form as they are handled by new fields/formset
        exclude = ['reference', 'documents', 'actions', 'subject', 'juridiction_steps']
        widgets = {
            'dossier_atmp': forms.HiddenInput(), # Still hidden, not directly user-editable
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # MODIFIED: Ensure 'status' field is required=False.
        # This tells the form to display the "---------" option for the status dropdown.
        self.fields['status'].required = False

        # Pre-populate subject_title and subject_description if editing an existing instance
        if self.instance.pk and isinstance(self.instance.subject, dict):
            self.initial['subject_title'] = self.instance.subject.get('title', '')
            self.initial['subject_description'] = self.instance.subject.get('description', '')

        # --- Initialize the Formset for juridiction_steps ---
        initial_steps_data = []
        if self.instance.pk and isinstance(self.instance.juridiction_steps, dict):
            # Sort the keys (e.g., 'step1', 'step2') to ensure consistent order
            sorted_keys = sorted(
                self.instance.juridiction_steps.keys(),
                key=lambda x: int(x.replace('step', '')) if x.startswith('step') and x[4:].isdigit() else float('inf')
            )
            for key in sorted_keys:
                step_data = self.instance.juridiction_steps[key]
                # Ensure date is in 'YYYY-MM-DD' format if coming from non-standard JSON
                step_date_str = step_data.get('date')
                if step_date_str:
                    try:
                        # Attempt to parse as date object for DateField
                        step_date_obj = forms.DateField().to_python(step_date_str)
                    except ValidationError:
                        step_date_obj = None # Or handle error appropriately
                else:
                    step_date_obj = None

                initial_steps_data.append({
                    'step_type': step_data.get('type', ''),
                    'step_date': step_date_obj,
                    'step_notes': step_data.get('notes', ''),
                })

        # Define the formset factory for juridiction steps
        # extra=1: display one empty form for new Contentieux creation
        # can_delete=True: allows steps to be marked for deletion (requires template/JS support)
        JuridictionStepFormSet = formset_factory(JuridictionStepForm, extra=1, can_delete=True)

        self.juridiction_step_formset = JuridictionStepFormSet(
            self.data if self.is_bound else None, # Pass form data on POST, or None on GET
            initial=initial_steps_data,
            prefix='juridiction_steps' # Important for isolating formset data in POST
        )

    def is_valid(self):
        # Validate main form and formset
        main_form_valid = super().is_valid()
        formset_valid = self.juridiction_step_formset.is_valid()
        
        # Transfer formset errors to the main form's non_field_errors for display
        if not formset_valid:
            for i, form_errors in enumerate(self.juridiction_step_formset.errors):
                if form_errors: # If there are errors in this specific form
                    for field, errors in form_errors.items():
                        self.add_error(None, f"Juridiction Step {i+1} - {field}: {', '.join(errors)}")
        
        return main_form_valid and formset_valid

    def save(self, commit=True):
        instance = super().save(commit=False) # Get the Contentieux instance but don't save to DB yet

        # Combine subject_title and subject_description into the JSON 'subject' field
        instance.subject = {
            'title': self.cleaned_data['subject_title'],
            'description': self.cleaned_data['subject_description'],
        }

        # Process juridiction_steps from the formset
        cleaned_steps = {}
        # Iterate over formset forms, only processing those that are valid and not marked for deletion
        # form.cleaned_data will be {} if the form is empty, or if marked for deletion and no data changed.
        for i, form in enumerate(self.juridiction_step_formset):
            if form.is_valid() and not form.cleaned_data.get('DELETE'):
                step_data = {
                    'type': form.cleaned_data['step_type'],
                    'date': form.cleaned_data['step_date'].isoformat() if form.cleaned_data['step_date'] else None,
                    'notes': form.cleaned_data['step_notes'],
                }
                cleaned_steps[f'step{i+1}'] = step_data # Assign a simple key, e.g., 'step1', 'step2'

        instance.juridiction_steps = cleaned_steps

        if commit:
            instance.save()
            # If you enable ManyToMany fields like 'documents' or 'actions' as form fields,
            # you would need to call self.save_m2m() here.
            # E.g., if 'documents' was added to 'fields' in Meta:
            # self.save_m2m()

        return instance


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file', 'description', 'contentieux']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contentieux': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'contentieux' in self.fields:
            self.fields['contentieux'].required = False
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 10 * 1024 * 1024
            if file.size > max_size:
                raise forms.ValidationError(f"File too large. Size should not exceed {max_size/1024/1024}MB.")
        return file


class TemoinForm(forms.ModelForm):
    class Meta:
        model = Temoin
        fields = ['nom', 'coordonnees']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Full Name")}),
            'coordonnees': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Phone, Email, or Address")}),
        }
        labels = {
            'nom': _("Witness Name"),
            'coordonnees': _("Contact Information"),
        }

    # Optional: Add custom validation for TemoinForm if needed
    def clean(self):
        cleaned_data = super().clean()
        nom = cleaned_data.get('nom')
        coordonnees = cleaned_data.get('coordonnees')

        # Example: If a name is provided, contact info should also be provided (or vice versa)
        if nom and not coordonnees:
            self.add_error('coordonnees', _("Contact information is required if a witness name is provided."))
        elif coordonnees and not nom:
            self.add_error('nom', _("Witness name is required if contact information is provided."))

        return cleaned_data


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'email']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _("Full Name"),
            'email': _("Email Address"),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        # Ensure email uniqueness, but allow the current user's existing email
        if self.instance.pk: # If this is an update form
            if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(_("This email address is already in use by another account."))
        else: # This path is less likely for a profile *edit* form, but good for completeness
            if CustomUser.objects.filter(email=email).exists():
                raise forms.ValidationError(_("This email address is already in use."))
        return email
