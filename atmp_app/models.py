# /atmp/atmp_app/models.py

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------- #
#            Enums            #
# ---------------------------- #

class AuditDecision(models.TextChoices):
    CONTEST = 'CONTEST', 'Contest'
    DO_NOT_CONTEST = 'DO_NOT_CONTEST', 'Do Not Contest'
    NEED_MORE_INFO = 'NEED_MORE_INFO', 'Need More Info'
    REFER_TO_EXPERT = 'REFER_TO_EXPERT', 'Refer To Expert'


class AuditStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'


class DossierStatus(models.TextChoices):
    A_ANALYSER = 'A_ANALYSER', 'À Analyser'
    ANALYSE_EN_COURS = 'ANALYSE_EN_COURS', 'Analyse en Cours'
    CONTESTATION_RECOMMANDEE = 'CONTESTATION_RECOMMANDEE', 'Contestation Recommandée'
    CLOTURE_SANS_SUITE = 'CLOTURE_SANS_SUITE', 'Clôture Sans Suite'
    TRANSFORME_EN_CONTENTIEUX = 'TRANSFORME_EN_CONTENTIEUX', 'Transformé en Contentieux'


class ContentieuxStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    EN_COURS = 'EN_COURS', 'En Cours'
    CLOTURE = 'CLOTURE', 'Clôturé'


class JuridictionType(models.TextChoices):
    TRIBUNAL_JUDICIAIRE = 'TRIBUNAL_JUDICIAIRE', 'Tribunal Judiciaire'
    COUR_APPEL = 'COUR_APPEL', 'Cour d\'Appel'
    COUR_CASSATION = 'COUR_CASSATION', 'Cour de Cassation'


class DocumentType(models.TextChoices):
    DAT = 'DAT', 'DAT'
    CERTIFICAT_MEDICAL = 'CERTIFICAT_MEDICAL', 'Certificat Médical'
    ARRET_TRAVAIL = 'ARRET_TRAVAIL', 'Arrêt de Travail'
    TEMOIGNAGE = 'TEMOIGNAGE', 'Témoignage'
    DECISION_CPAM = 'DECISION_CPAM', 'Décision CPAM'
    EXPERTISE_MEDICALE = 'EXPERTISE_MEDICALE', 'Expertise Médicale'
    LETTRE_RESERVE = 'LETTRE_RESERVE', 'Lettre de Réserve'
    CONTRAT_TRAVAIL = 'CONTRAT_TRAVAIL', 'Contrat de Travail'
    FICHE_POSTE = 'FICHE_POSTE', 'Fiche de Poste'
    RAPPORT_ENQUETE = 'RAPPORT_ENQUETE', 'Rapport d’Enquête'
    NOTIFICATION_TAUX = 'NOTIFICATION_TAUX', 'Notification de Taux'
    COURRIER = 'COURRIER', 'Courrier'
    AUTRE = 'AUTRE', 'Autre'

# ---------------------------- #
#           Models            #
# ---------------------------- #

class Action(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Action'
        verbose_name_plural = 'Actions'

    def __str__(self):
        return self.name


class Document(models.Model):
    contentieux = models.ForeignKey('Contentieux', on_delete=models.CASCADE, related_name='document_set', null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_documents')
    document_type = models.CharField(max_length=50, choices=DocumentType.choices, null=True, blank=True)
    original_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='documents/%Y/%m/%d/', blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        # Provide a fallback if original_name is null
        return self.original_name or f"Document (ID: {self.pk})"

    def save(self, *args, **kwargs):
        if self.file:
            if not self.original_name:
                 self.original_name = self.file.name

            if not self.mime_type and self.file.file:
                self.mime_type = self.file.file.content_type
            
            if not self.size:
                self.size = self.file.size

        else:
            self.original_name = None
            self.mime_type = None
            self.size = None
            
        super().save(*args, **kwargs)


class DossierATMP(models.Model):
    reference = models.CharField(max_length=255, unique=True, blank=True)
    safety_manager = models.ForeignKey(User, on_delete=models.PROTECT, related_name='managed_dossiers')
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_of_incident = models.DateField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=DossierStatus.choices)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_dossiers')


    entreprise = models.JSONField(blank=True, null=True)
    salarie = models.JSONField(blank=True, null=True)
    accident = models.JSONField(blank=True, null=True)
    # REMOVED: temoins = models.JSONField(default=list, blank=True, null=True) 
    tiers_implique = models.JSONField(blank=True, null=True)
    service_sante = models.CharField(max_length=255, blank=True, null=True)

    documents = models.ManyToManyField(Document, related_name='dossier_atmp_documents', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dossier AT/MP'
        verbose_name_plural = 'Dossiers AT/MP'

    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate a unique reference if it's not set
            self.reference = f"ATMP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Convert empty JSONField dicts/lists to None for database storage if preferred
        if self.entreprise == {}:
            self.entreprise = None
        if self.salarie == {}:
            self.salarie = None
        if self.accident == {}:
            self.accident = None
        if self.tiers_implique == {}:
            self.tiers_implique = None
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class Contentieux(models.Model):
    dossier_atmp = models.OneToOneField(DossierATMP, on_delete=models.CASCADE, related_name='contentieux')
    reference = models.CharField(max_length=255, unique=True, blank=True, null=True)
    subject = models.JSONField()
    status = models.CharField(max_length=50, choices=ContentieuxStatus.choices, default=ContentieuxStatus.DRAFT, null=True, blank=True)
    juridiction_steps = models.JSONField(default=dict)
    documents = models.ManyToManyField(Document, related_name='contentieux_documents', blank=True)
    actions = models.ManyToManyField(Action, related_name='contentieux_actions', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contentieux'
        verbose_name_plural = 'Contentieux'

    def __str__(self):
        return self.reference or f"New Contentieux for {self.dossier_atmp.reference}"

    # Add a save method to auto-generate the reference
    def save(self, *args, **kwargs):
        if not self.reference: # Only generate if it's not set (e.g., for new instances)
            # You can base this on dossier reference, or just a new unique string
            self.reference = f"CTX-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Audit(models.Model):
    dossier_atmp = models.OneToOneField(DossierATMP, on_delete=models.CASCADE, related_name='audit')
    auditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audits')
    status = models.CharField(max_length=50, choices=AuditStatus.choices, default=AuditStatus.NOT_STARTED)
    decision = models.CharField(max_length=50, choices=AuditDecision.choices, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit'
        verbose_name_plural = 'Audits'

    def __str__(self):
        return f"Audit for {self.dossier_atmp.reference}"


class AuditChecklistItem(models.Model):
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='checklist_items')
    question = models.CharField(max_length=500)
    answer = models.BooleanField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    document_required = models.BooleanField(default=False)
    document_received = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Audit Checklist Item'
        verbose_name_plural = 'Audit Checklist Items'

    def __str__(self):
        return self.question if len(self.question) <= 50 else self.question[:47] + "..."


class JuridictionStep(models.Model):
    contentieux = models.ForeignKey(Contentieux, on_delete=models.CASCADE, related_name='juridiction_steps_set')
    juridiction = models.CharField(max_length=50, choices=JuridictionType.choices, null=True, blank=True)
    submitted_at = models.DateTimeField()
    decision = models.CharField(max_length=50, choices=[('FAVORABLE', 'Favorable'), ('DEFAVORABLE', 'Défavorable')], blank=True, null=True)
    decision_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Juridiction Step'
        verbose_name_plural = 'Juridiction Steps'

    def __str__(self):
        return f"{self.juridiction} ({self.submitted_at.date()})"


class Temoin(models.Model):
    dossier_atmp = models.ForeignKey(DossierATMP, on_delete=models.CASCADE, related_name='temoin_set')
    nom = models.CharField(max_length=255)
    coordonnees = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'Témoin'
        verbose_name_plural = 'Témoins'

    def __str__(self):
        return self.nom


class Tiers(models.Model):
    dossier_atmp = models.OneToOneField(DossierATMP, on_delete=models.CASCADE, related_name='tiers')
    nom = models.CharField(max_length=255, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    assurance = models.CharField(max_length=255, blank=True, null=True)
    immatriculation = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'Tiers Impliqué'
        verbose_name_plural = 'Tiers Impliqués'

    def __str__(self):
        return self.nom or "Tiers Impliqué"
