# /home/siisi/atmp/atmp_app/forms.py

from django import forms
from django.contrib.auth import get_user_model

from .models import DossierATMP, Contentieux, Document

User = get_user_model()


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name or obj.email


class DossierATMPForm(forms.ModelForm):
    """
    Form to create/edit a DossierATMP.
    """
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role='safety_manager'),
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
            'date_of_incident',
            'location',
            'status'
        ]
        widgets = {
            'reference':   forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location':    forms.TextInput(attrs={'class': 'form-control'}),
            'status':      forms.Select(attrs={'class': 'form-select'}),
        }


class ContentieuxForm(forms.ModelForm):
    """
    Form to create/edit a Contentieux linked to a DossierATMP.
    """
    dossier_atmp = forms.ModelChoiceField(
        queryset=DossierATMP.objects.all(),
        label="Dossier ATMP",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Contentieux
        fields = [
            'dossier_atmp',
            'reference',
            'status',
            'subject',
            'juridiction_steps'
        ]
        widgets = {
            'reference':         forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'status':            forms.Select(attrs={'class': 'form-select'}),
            'subject':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'juridiction_steps': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DocumentForm(forms.ModelForm):
    """
    Form to upload a Document for a specific Contentieux.
    """
    contentieux = forms.ModelChoiceField(
        queryset=Contentieux.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Document
        fields = [
            'contentieux',
            'uploaded_by',
            'file',
            'document_type',
            'original_name'
        ]
        widgets = {
            'uploaded_by':   forms.Select(attrs={'class': 'form-select'}),
            'file':          forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'original_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
