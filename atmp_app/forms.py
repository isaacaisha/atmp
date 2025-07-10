# /home/siisi/atmp/atmp_app/forms.py

from django import forms
from django.contrib.auth import get_user_model
from .models import ATMPIncident

User = get_user_model()


class SafetyManagerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name or obj.email


class IncidentForm(forms.ModelForm):
    safety_manager = SafetyManagerChoiceField(
        queryset=User.objects.filter(role='safety_manager'),
        label="Safety Manager",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
    )
    date_of_incident = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    location = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    STATUS_CHOICES = [('', 'Select a status')] + ATMPIncident.STATUS_CHOICES
    status = forms.ChoiceField(
        choices=ATMPIncident.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
    )

    document = forms.FileField(
        required=False,
        label="Attach a Document",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
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
            'document',
        ]
