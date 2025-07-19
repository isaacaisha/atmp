# /home/siisi/atmp/atmp_app/models.py

from django.db import models
from django.contrib.auth import get_user_model 
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone
import enum

User = get_user_model()

# ───────────────────────────────────────────────────────────────
# ENUMS (unchanged)
# ───────────────────────────────────────────────────────────────
class AuditDecision(enum.Enum):
    CONTEST = 'CONTEST'
    DO_NOT_CONTEST = 'DO_NOT_CONTEST'
    NEED_MORE_INFO = 'NEED_MORE_INFO'
    REFER_TO_EXPERT = 'REFER_TO_EXPERT'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class AuditStatus(enum.Enum):
    NOT_STARTED = 'NOT_STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class ContentieuxStatus(enum.Enum):
    DRAFT = 'DRAFT'
    EN_COURS = 'EN_COURS'
    CLOTURE = 'CLOTURE'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class JuridictionType(enum.Enum):
    TRIBUNAL_JUDICIAIRE = 'TRIBUNAL_JUDICIAIRE'
    COUR_APPEL          = 'COUR_APPEL'
    COUR_CASSATION      = 'COUR_CASSATION'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class DocumentType(enum.Enum):
    DAT = 'DAT'
    CERTIFICAT_MEDICAL = 'CERTIFICAT_MEDICAL'
    ARRET_TRAVAIL = 'ARRET_TRAVAIL'
    TEMOIGNAGE = 'TEMOIGNAGE'
    DECISION_CPAM = 'DECISION_CPAM'
    EXPERTISE_MEDICALE = 'EXPERTISE_MEDICALE'
    LETTRE_RESERVE = 'LETTRE_RESERVE'
    CONTRAT_TRAVAIL = 'CONTRAT_TRAVAIL'
    FICHE_POSTE = 'FICHE_POSTE'
    RAPPORT_ENQUETE = 'RAPPORT_ENQUETE'
    NOTIFICATION_TAUX = 'NOTIFICATION_TAUX'
    COURRIER = 'COURRIER'
    AUTRE = 'AUTRE'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class DossierStatus(enum.Enum):
    A_ANALYSER = 'A_ANALYSER'
    ANALYSE_EN_COURS = 'ANALYSE_EN_COURS'
    CONTESTATION_RECOMMANDEE = 'CONTESTATION_RECOMMANDEE'
    CONTESTATION_NON_RECOMMANDEE = 'CONTESTATION_NON_RECOMMANDEE'
    CLOTURE_SANS_SUITE = 'CLOTURE_SANS_SUITE'
    TRANSFORME_EN_CONTENTIEUX = 'TRANSFORME_EN_CONTENTIEUX'
    @classmethod
    def choices(cls): return [(m.value, m.name) for m in cls]

class UserRole:
    ADMIN = 'ADMIN'
    JURISTE = 'JURISTE'
    RH = 'RH'
    MANAGER = 'MANAGER'
    @staticmethod
    def choices():
        return [
            (UserRole.ADMIN,  'Admin'),
            (UserRole.JURISTE, 'Jurist'),
            (UserRole.RH,  'Rh'),
            (UserRole.MANAGER,  'Manager'),
        ]

# ───────────────────────────────────────────────────────────────
#  OTHER MODELS  (only FK/M2M changed to settings.AUTH_USER_MODEL)
# ───────────────────────────────────────────────────────────────
class Action(models.Model):
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    class Meta:
        db_table  = 'actions'
        ordering  = ['-created_at']
    def __str__(self): return self.name

class Document(models.Model):
    contentieux   = models.ForeignKey('Contentieux', on_delete=models.CASCADE, related_name='documents_list')
    uploaded_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_documents')
    document_type = models.CharField(max_length=50, choices=DocumentType.choices())
    original_name = models.CharField(max_length=255)
    file          = models.FileField(upload_to='documents/', blank=True, null=True)
    mime_type     = models.CharField(max_length=100)
    size          = models.IntegerField()
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
    def __str__(self): return self.original_name

class Contentieux(models.Model):
    dossier_atmp      = models.OneToOneField('DossierATMP', on_delete=models.CASCADE, related_name='contentieux_detail')
    reference         = models.CharField(max_length=255, unique=True)
    subject           = models.JSONField()
    status            = models.CharField(max_length=50, choices=ContentieuxStatus.choices())
    juridiction_steps = models.JSONField(default=dict)
    documents         = models.ManyToManyField(Document, related_name='contentieux_documents', blank=True)
    actions           = models.ManyToManyField(Action, related_name='contentieux_actions', blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'contentieux'
        ordering = ['-created_at']
    def __str__(self): return self.reference

class DossierATMP(models.Model):
    reference        = models.CharField(max_length=255, unique=True)
    safety_manager   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, limit_choices_to={'role':'safety_manager'})
    title            = models.CharField(max_length=255)
    description      = models.TextField()
    date_of_incident = models.DateField()
    location         = models.CharField(max_length=255)
    status           = models.CharField(max_length=50, choices=DossierStatus.choices(), default=DossierStatus.A_ANALYSER.value)
    created_by       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_dossiers')
    entreprise       = models.JSONField()
    salarie          = models.JSONField()
    accident         = models.JSONField()
    temoins          = models.JSONField(default=list)
    tiers_implique   = models.JSONField(blank=True, null=True)
    service_sante    = models.CharField(max_length=255, blank=True, null=True)
    documents        = models.ManyToManyField(Document, related_name='dossier_atmp_documents', blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'dossiers_atmp'
        ordering = ['-created_at']
    def __str__(self): return self.reference


# --- Document Model (Now a Django ORM Model) ---
class UploadedFile(models.Model):
    contentieux = models.ForeignKey('Contentieux', on_delete=models.CASCADE, related_name='documents_set')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files_set')
    document_type = models.CharField(max_length=50, choices=[(dt.value, dt.value) for dt in DocumentType])
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    filename = models.CharField(max_length=255, blank=True, null=True)
    path = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Uploaded File'
        verbose_name_plural = 'Uploaded Files'

    def __str__(self):
        return self.original_name


# --- Audit Checklist Item (Now a Django ORM Model) ---
class AuditChecklistItem(models.Model):
    audit = models.ForeignKey('Audit', on_delete=models.CASCADE, related_name='checklist_items')
    question = models.CharField(max_length=500)
    answer = models.BooleanField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    document_required = models.BooleanField(default=False)
    document_received = models.BooleanField(default=False)

    def __str__(self):
        return self.question[:50] + "..." if len(self.question) > 50 else self.question

    class Meta:
        verbose_name = 'Audit Checklist Item'
        verbose_name_plural = 'Audit Checklist Items'


class Audit(models.Model):
    dossier_atmp = models.OneToOneField(DossierATMP, on_delete=models.CASCADE, related_name='audit_detail', unique=True)
    auditor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audits_performed')
    status       = models.CharField(max_length=50, choices=AuditStatus.choices(), default=AuditStatus.NOT_STARTED.value)
    decision     = models.CharField(max_length=50, choices=AuditDecision.choices(), blank=True, null=True)
    comments     = models.TextField(blank=True, null=True)
    checklist    = models.JSONField(default=list)
    started_at   = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'audits'
        ordering = ['-created_at']
    def __str__(self): return f"Audit for {self.dossier_atmp.reference}"


# --- Juridiction Step (Now a Django ORM Model) ---
class JuridictionStep(models.Model):
    contentieux = models.ForeignKey('Contentieux', on_delete=models.CASCADE, related_name='juridiction_steps_set')
    juridiction = models.CharField(max_length=50, choices=[(jt.value, jt.value) for jt in JuridictionType])
    submitted_at = models.DateTimeField()
    decision = models.CharField(max_length=50, choices=[('FAVORABLE', 'FAVORABLE'), ('DEFAVORABLE', 'DEFAVORABLE')], null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.juridiction} ({self.submitted_at.strftime('%Y-%m-%d')})"

    class Meta:
        verbose_name = 'Juridiction Step'
        verbose_name_plural = 'Juridiction Steps'


# --- Temoin (Now a Django ORM Model) ---
class Temoin(models.Model):
    dossier_atmp = models.ForeignKey('DossierATMP', on_delete=models.CASCADE, related_name='temoins_set')
    nom = models.CharField(max_length=255)
    coordonnees = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = 'Temoin'
        verbose_name_plural = 'Temoins'


# --- Tiers (Now a Django ORM Model) ---
class Tiers(models.Model):
    dossier_atmp = models.OneToOneField('DossierATMP', on_delete=models.CASCADE, related_name='tiers_implique_record', primary_key=True)
    nom = models.CharField(max_length=255, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    assurance = models.CharField(max_length=255, blank=True, null=True)
    immatriculation = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nom if self.nom else "Tiers Impliqué"

    class Meta:
        verbose_name = 'Tiers Impliqué'
        verbose_name_plural = 'Tiers Impliqués'


#import os
#from django.db import models
#from django.conf import settings
#from django.core.exceptions import ValidationError
#
#
#def validate_file_extension(value):
#    ext = os.path.splitext(value.name)[1]
#    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.webp']
#    if not ext.lower() in valid_extensions:
#        raise ValidationError('Unsupported file extension.')
#
#
#class ATMPIncident(models.Model):
#    STATUS_CHOICES = [
#        ('', 'Select a choice'),
#        ('declared', 'Declared'),
#        ('in_progress', 'In Progress'),
#        ('closed', 'Closed'),
#    ]
#    
#    provider = models.ForeignKey(
#        settings.AUTH_USER_MODEL,
#        on_delete=models.CASCADE,
#        related_name='provider_incidents',
#        limit_choices_to={'role': 'employee'}
#    )
#    safety_manager = models.ForeignKey(
#        settings.AUTH_USER_MODEL,
#        on_delete=models.CASCADE,
#        related_name='safety_manager_incidents',
#        limit_choices_to={'role': 'safety_manager'}
#    )
#    title = models.CharField(max_length=255)
#    description = models.TextField()
#    date_of_incident = models.DateField()
#    location = models.CharField(max_length=255)
#    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=False)
#    created_at = models.DateTimeField(auto_now_add=True)
#
#    def __str__(self):
#        return f"{self.title} ({self.status})"
#
#
#class ATMPDocument(models.Model):
#    incident = models.ForeignKey(ATMPIncident, on_delete=models.CASCADE, related_name='documents')
#    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#    file = models.FileField(
#        upload_to='atmp_docs/%Y/%m/%d/',
#        validators=[validate_file_extension]
#    )
#    description = models.TextField(blank=True)
#    uploaded_at = models.DateTimeField(auto_now_add=True)
#
#    def __str__(self):
#        return f"Document: {os.path.basename(self.file.name)}"
#