# /home/siisi/atmp/atmp_app/forms.py

import json
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import DossierATMP, Contentieux, Document, DocumentType, DossierStatus
from users.models import UserRole # Import UserRole


User = get_user_model()


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email


class EntrepriseForm(forms.Form):
    name = forms.CharField(max_length=255, required=True,
                           widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(max_length=255, required=True, # Changed to required=True to match serializer validation
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    siret = forms.CharField(max_length=14, required=True, # Changed to required=True to match serializer validation
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            help_text="14-digit SIRET number")


class SalarieForm(forms.Form):
    first_name = forms.CharField(max_length=100, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    social_security_number = forms.CharField(max_length=15, required=True, # Added to match serializer validation
                                              widget=forms.TextInput(attrs={'class': 'form-control'}),
                                              help_text="e.g., 179052A12345678")
    date_of_birth = forms.DateField(required=False,
                                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    job_title = forms.CharField(max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))


class AccidentForm(forms.Form):
    date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})) # Added to match serializer validation
    time = forms.TimeField(required=True, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})) # Added to match serializer validation
    description = forms.CharField(required=True, # Added to match serializer validation
                                  widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    type_of_accident = forms.CharField(max_length=255, required=False, 
                                       widget=forms.TextInput(attrs={'class': 'form-control'}))
    detailed_circumstances = forms.CharField(required=True,
                                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


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
            # 'temoins', 'tiers_implique' - these were JSONFields, now only 'tiers_implique' remains as JSONField
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
        
        return main_form_valid and entreprise_form_valid and salarie_form_valid and accident_form_valid

    def clean(self):
        cleaned_data = super().clean()

        if self.entreprise_form.is_valid():
            cleaned_data['entreprise'] = self.entreprise_form.cleaned_data
        else:
            for field, errors in self.entreprise_form.errors.items():
                self.add_error(f'entreprise-{field}', errors) 
            if not self.entreprise_form.non_field_errors():
                 self.add_error(None, "Please correct errors in the Company Details section.")


        if self.salarie_form.is_valid():
            cleaned_data['salarie'] = self.salarie_form.cleaned_data
        else:
            for field, errors in self.salarie_form.errors.items():
                self.add_error(f'salarie-{field}', errors)
            if not self.salarie_form.non_field_errors():
                self.add_error(None, "Please correct errors in the Employee Details section.")

        if self.accident_form.is_valid():
            cleaned_data['accident'] = self.accident_form.cleaned_data
        else:
            for field, errors in self.accident_form.errors.items():
                self.add_error(f'accident-{field}', errors)
            if not self.accident_form.non_field_errors():
                self.add_error(None, "Please correct errors in the Accident Details section.")

        uploaded_file = cleaned_data.get('uploaded_file')
        document_type = cleaned_data.get('document_type')

        if uploaded_file and not document_type:
            self.add_error('document_type', "Document type is required if a file is uploaded.")
        elif document_type and not uploaded_file:
             self.add_error('uploaded_file', "A file is required if document type is selected.")

        return cleaned_data

    def clean_uploaded_file(self):
        file = self.cleaned_data.get('uploaded_file')
        if file:
            max_size = 10 * 1024 * 1024 
            if file.size > max_size:
                raise ValidationError(f"File too large. Size should not exceed {max_size/1024/1024:.0f}MB.")
        return file


class ContentieuxForm(forms.ModelForm):
    class Meta:
        model = Contentieux
        fields = [
            'dossier_atmp',
            'subject',
            'status',
            'juridiction_steps', 
        ]
        widgets = {
            'dossier_atmp': forms.Select(attrs={'class': 'form-select', 'readonly': 'readonly'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'juridiction_steps': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}), 
        }

    def clean_subject(self):
        data = self.cleaned_data['subject']
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for Subject.")
        return data

    def clean_juridiction_steps(self):
        data = self.cleaned_data['juridiction_steps']
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for Juridiction Steps.")
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if isinstance(self.instance.subject, dict):
                self.initial['subject'] = json.dumps(self.instance.subject, indent=2)
            if isinstance(self.instance.juridiction_steps, dict):
                self.initial['juridiction_steps'] = json.dumps(self.instance.juridiction_steps, indent=2)


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
