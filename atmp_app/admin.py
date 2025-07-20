# /home/siisi/atmp/atmp_app/admin.py

from django.contrib import admin

from .models import (
    Action, Document, Contentieux, DossierATMP,
    Audit, UploadedFile, AuditChecklistItem,
    JuridictionStep, Temoin, Tiers
)


# ───────────────────────────────
# Document Admin
# ───────────────────────────────
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'document_type', 'uploaded_by', 'contentieux', 'created_at')
    list_filter = ('document_type',)
    search_fields = ('original_name', 'mime_type')
    ordering = ('-created_at',)

# ───────────────────────────────
# Contentieux Admin
# ───────────────────────────────
@admin.register(Contentieux)
class ContentieuxAdmin(admin.ModelAdmin):
    list_display = ('reference', 'dossier_atmp', 'status', 'created_at')
    search_fields = ('reference',)
    list_filter = ('status',)
    ordering = ('-created_at',)

# ───────────────────────────────
# DossierATMP Admin
# ───────────────────────────────
@admin.register(DossierATMP)
class DossierATMPAdmin(admin.ModelAdmin):
    list_display = ('reference', 'status', 'created_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('reference', 'created_by__email')
    ordering = ('-created_at',)

# ───────────────────────────────
# Audit Admin
# ───────────────────────────────
@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('dossier_atmp', 'auditor', 'status', 'decision', 'created_at')
    list_filter = ('status', 'decision')
    search_fields = ('dossier_atmp__reference', 'auditor__email')
    ordering = ('-created_at',)

# ───────────────────────────────
# Action Admin
# ───────────────────────────────
@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

# ───────────────────────────────
# UploadedFile Admin
# ───────────────────────────────
admin.site.register(UploadedFile)

# ───────────────────────────────
# AuditChecklistItem Admin
# ───────────────────────────────
admin.site.register(AuditChecklistItem)

# ───────────────────────────────
# JuridictionStep Admin
# ───────────────────────────────
admin.site.register(JuridictionStep)

# ───────────────────────────────
# Temoin Admin
# ───────────────────────────────
admin.site.register(Temoin)

# ───────────────────────────────
# Tiers Admin
# ───────────────────────────────
admin.site.register(Tiers)
