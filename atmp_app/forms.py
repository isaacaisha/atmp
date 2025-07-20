# /home/siisi/atmp/atmp_app/forms.py

import json
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import DossierATMP, Contentieux, Document, DocumentType, DossierStatus

User = get_user_model()


class JSONEditorWidget(forms.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, indent=2)
        return super().render(name, value, attrs, renderer)


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email


class EntrepriseForm(forms.Form):
    name = forms.CharField(max_length=255, required=True,
                           widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(max_length=255, required=False,
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    siret = forms.CharField(max_length=14, required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            help_text="14-digit SIRET number")
    # Add other fields as per your 'entreprise' JSON structure

# New Form for Salarie JSON data
class SalarieForm(forms.Form):
    first_name = forms.CharField(max_length=100, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_of_birth = forms.DateField(required=False,
                                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    job_title = forms.CharField(max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Add other fields as per your 'salarie' JSON structure

# New Form for Accident JSON data
class AccidentForm(forms.Form):
    type_of_accident = forms.CharField(max_length=255, required=True,
                                       widget=forms.TextInput(attrs={'class': 'form-control'}))
    detailed_circumstances = forms.CharField(required=True,
                                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    # You might have fields like 'body_part_affected', 'material_involved', etc.
    # For example:
    # body_part_affected = forms.CharField(max_length=255, required=False,
    #                                      widget=forms.TextInput(attrs={'class': 'form-control'}))


class DossierATMPForm(forms.ModelForm):
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role='SAFETY_MANAGER'),
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

    # NO LONGER NEEDED AS THEY ARE HANDLED BY SUB-FORMS:
    # entreprise = forms.CharField(widget=JSONEditorWidget(...), required=False)
    # salarie = forms.CharField(widget=JSONEditorWidget(...), required=False)
    # accident = forms.CharField(widget=JSONEditorWidget(...), required=False)


    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Instantiate the nested forms
        # Pass initial data if updating an existing incident
        initial_entreprise_data = self.instance.entreprise if self.instance and self.instance.entreprise else {}
        initial_salarie_data = self.instance.salarie if self.instance and self.instance.salarie else {}
        initial_accident_data = self.instance.accident if self.instance and self.instance.accident else {}

        # Add prefixes to avoid field name collisions (important!)
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
            # 'temoins', 'tiers_implique' - if you want to handle these JSONFields similarly
        ]
        widgets = {
            'reference':   forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            # REMOVE JSONEditorWidget entries for entreprise, salarie, accident
            'service_sante': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def is_valid(self):
        # Validate all forms: the main form and the nested forms
        main_form_valid = super().is_valid()
        entreprise_form_valid = self.entreprise_form.is_valid()
        salarie_form_valid = self.salarie_form.is_valid()
        accident_form_valid = self.accident_form.is_valid()
        return main_form_valid and entreprise_form_valid and salarie_form_valid and accident_form_valid

    def clean(self):
        cleaned_data = super().clean()

        # Merge cleaned data from nested forms into the main cleaned_data
        if self.entreprise_form.is_valid():
            cleaned_data['entreprise'] = self.entreprise_form.cleaned_data
        if self.salarie_form.is_valid():
            cleaned_data['salarie'] = self.salarie_form.cleaned_data
        if self.accident_form.is_valid():
            cleaned_data['accident'] = self.accident_form.cleaned_data

        # --- Your existing file upload validation ---
        uploaded_file = cleaned_data.get('uploaded_file')
        document_type = cleaned_data.get('document_type')

        if uploaded_file and not document_type:
            self.add_error('document_type', "Document type is required if a file is uploaded.")
        elif document_type and not uploaded_file:
             self.add_error('uploaded_file', "A file is required if document type is selected.")
        # --- End existing file upload validation ---

        return cleaned_data

    # Add a clean method for the uploaded_file to perform validation
    def clean_uploaded_file(self):
        file = self.cleaned_data.get('uploaded_file')
        if file:
            max_size = 10 * 1024 * 1024 # 10MB
            if file.size > max_size:
                raise ValidationError(f"File too large. Size should not exceed {max_size/1024/1024:.0f}MB.")
        return file


class ContentieuxForm(forms.ModelForm):
    class Meta:
        model = Contentieux
        fields = [
            'dossier_atmp',
            'subject',
            'status'
        ]
        widgets = {
            'dossier_atmp': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


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
        # Make contentieux optional if it exists in fields
        if 'contentieux' in self.fields:
            self.fields['contentieux'].required = False
            # Limit contentieux choices to those related to the dossier
            if 'initial' in kwargs and 'contentieux' in kwargs['initial']:
                self.fields['contentieux'].queryset = Contentieux.objects.filter(
                    dossier_atmp=kwargs['initial']['contentieux'].dossier_atmp
                )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate file size (e.g., 10MB max)
            max_size = 10 * 1024 * 1024
            if file.size > max_size:
                raise forms.ValidationError(f"File too large. Size should not exceed {max_size/1024/1024}MB.")
        return file
