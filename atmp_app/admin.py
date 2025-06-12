# /home/siisi/atmp/atmp_app/admin.py

from django.contrib import admin
from .models import ATMPIncident, ATMPDocument


class DocumentInline(admin.StackedInline):
    model = ATMPDocument
    extra = 1
    fields = ('file', 'uploaded_by', 'description', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(ATMPIncident)
class ATMPIncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'safety_manager', 'status', 'date_of_incident')
    list_filter = ('status', 'date_of_incident')
    search_fields = ('title', 'description', 'location')
    inlines = [DocumentInline]


@admin.register(ATMPDocument)
class ATMPDocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'incident', 'uploaded_by')
    list_filter = ('uploaded_at',)
    search_fields = ('description',)
