# /home/siisi/atmp/atmp_app/forms.py

import os
from django import forms
from django.contrib.auth import get_user_model
from .models import ATMPIncident

User = get_user_model()


class SafetyManagerChoiceField(forms.ModelChoiceField):
    """Show each safety manager by their name (fallback to email)."""
    def label_from_instance(self, obj):
        return obj.name or obj.email


class IncidentForm(forms.ModelForm):
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role='safety_manager'),
        label="Safety Manager",
    )
    
    document = forms.FileField(
        required=False,
        label='Attach a Document',
        widget=forms.ClearableFileInput()
    )

    class Meta:
        model = ATMPIncident
        fields = [
            'safety_manager',
            'title',
            'description',
            'date_of_incident',
            'location',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'date_of_incident': forms.DateInput(attrs={'type': 'date'}),
        }
