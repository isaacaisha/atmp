# /home/siisi/atmp/atmp_app/models.py

import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')


class ATMPIncident(models.Model):
    STATUS_CHOICES = [
        ('declared', 'Declared'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
    
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='provider_incidents',
        limit_choices_to={'role': 'employee'}
    )
    safety_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='safety_manager_incidents',
        limit_choices_to={'role': 'safety_manager'}
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_of_incident = models.DateField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='declared')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.status})"


class ATMPDocument(models.Model):
    incident = models.ForeignKey(ATMPIncident, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(
        upload_to='atmp_docs/%Y/%m/%d/',
        validators=[validate_file_extension]
    )
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document: {os.path.basename(self.file.name)}"
