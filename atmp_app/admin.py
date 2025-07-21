# /home/siisi/atmp/atmp_app/admin.py

from django.contrib import admin

from .models import (
    Action, Document, Contentieux, DossierATMP,
    Audit, AuditChecklistItem,
    JuridictionStep, Temoin, Tiers
)


# ───────────────────────────────
# Document Admin
# ───────────────────────────────
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'document_type', 'uploaded_by', 'contentieux', 'created_at')
    list_filter = ('document_type', 'uploaded_by')
    search_fields = ('original_name', 'mime_type', 'description')
    ordering = ('-created_at',)
    raw_id_fields = ('uploaded_by', 'contentieux') # Use raw_id_fields for FK to improve admin performance with many users/contentieux

# ───────────────────────────────
# Contentieux Admin
# ───────────────────────────────
@admin.register(Contentieux)
class ContentieuxAdmin(admin.ModelAdmin):
    list_display = ('reference', 'dossier_atmp', 'status', 'created_at')
    search_fields = ('reference', 'dossier_atmp__reference', 'subject')
    list_filter = ('status',)
    ordering = ('-created_at',)
    raw_id_fields = ('dossier_atmp',)

# ───────────────────────────────
# DossierATMP Admin
# ───────────────────────────────
@admin.register(DossierATMP)
class DossierATMPAdmin(admin.ModelAdmin):
    list_display = ('reference', 'title', 'status', 'created_by', 'safety_manager', 'created_at')
    list_filter = ('status', 'safety_manager', 'created_by')
    search_fields = ('reference', 'title', 'created_by__email', 'safety_manager__email')
    ordering = ('-created_at',)
    raw_id_fields = ('created_by', 'safety_manager')
    filter_horizontal = ('documents',)

# ───────────────────────────────
# Audit Admin
# ───────────────────────────────
@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('dossier_atmp', 'auditor', 'status', 'decision', 'created_at')
    list_filter = ('status', 'decision', 'auditor')
    search_fields = ('dossier_atmp__reference', 'auditor__email', 'comments')
    ordering = ('-created_at',)
    raw_id_fields = ('dossier_atmp', 'auditor')

# ───────────────────────────────
# Action Admin
# ───────────────────────────────
@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

# ───────────────────────────────
# AuditChecklistItem Admin
# ───────────────────────────────
@admin.register(AuditChecklistItem)
class AuditChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('audit', 'question', 'answer', 'document_required', 'document_received')
    list_filter = ('audit', 'answer', 'document_required', 'document_received')
    search_fields = ('question', 'comment')
    raw_id_fields = ('audit',)

# ───────────────────────────────
# JuridictionStep Admin
# ───────────────────────────────
@admin.register(JuridictionStep)
class JuridictionStepAdmin(admin.ModelAdmin):
    list_display = ('contentieux', 'juridiction', 'submitted_at', 'decision', 'decision_at')
    list_filter = ('juridiction', 'decision')
    search_fields = ('contentieux__reference', 'notes')
    raw_id_fields = ('contentieux',)

# ───────────────────────────────
# Temoin Admin
# ───────────────────────────────
@admin.register(Temoin)
class TemoinAdmin(admin.ModelAdmin):
    list_display = ('nom', 'dossier_atmp', 'coordonnees')
    search_fields = ('nom', 'coordonnees', 'dossier_atmp__reference')
    raw_id_fields = ('dossier_atmp',)

# ───────────────────────────────
# Tiers Admin
# ───────────────────────────────
@admin.register(Tiers)
class TiersAdmin(admin.ModelAdmin):
    list_display = ('nom', 'dossier_atmp', 'assurance')
    search_fields = ('nom', 'adresse', 'assurance', 'immatriculation', 'dossier_atmp__reference')
    raw_id_fields = ('dossier_atmp',)
