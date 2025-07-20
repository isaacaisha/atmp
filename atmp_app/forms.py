# /home/siisi/atmp/atmp_app/forms.py

import json
from django import forms
from django.contrib.auth import get_user_model

from .models import DossierATMP, Contentieux, Document

User = get_user_model()


class JSONEditorWidget(forms.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, indent=2)
        return super().render(name, value, attrs, renderer)


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.email


class DossierATMPForm(forms.ModelForm):
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role='SAFETY_MANAGER'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_incident = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
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
            'entreprise',
            'salarie',
            'accident',
            'service_sante',
        ]
        widgets = {
            'reference':   forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'entreprise': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'salarie': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'accident': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'service_sante': forms.TextInput(attrs={'class': 'form-control'}),
        }


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
