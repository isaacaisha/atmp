# atmp_app/management/commands/seed_data.py

from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from atmp_app.models import (
    DossierATMP, DossierStatus,
    Contentieux, ContentieuxStatus,
    Document, DocumentType,
    Audit, AuditStatus, AuditDecision,
    Action,
)
from users.models import CustomUser as User


class Command(BaseCommand):
    help = 'Seeds the database with initial data for testing and development.'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting data seeding…")

        with transaction.atomic():
            # 1) wipe existing data
            Audit.objects.all().delete()
            Contentieux.objects.all().delete()
            DossierATMP.objects.all().delete()
            Document.objects.all().delete()
            Action.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write("🗑️  Cleared old rows")

            # 2) Create users via create_user (no username field!)
            admin = User.objects.create_user(
                email='admin@example.com',
                password='secret',
                name='Admin User',
                role='ADMIN',
                is_staff=True,
                is_superuser=True
            )
            juriste = User.objects.create_user(
                email='juriste@example.com',
                password='juriste123',
                name='Juriste Alpha',
                role='JURISTE'
            )
            rh = User.objects.create_user(
                email='rh@example.com',
                password='rh123',
                name='RH Beta',
                role='RH'
            )
            self.stdout.write(self.style.SUCCESS("✅ Users created"))

            # 3) Dossier ATMP
            dossier = DossierATMP.objects.create(
                reference=f"DAT-{int(datetime.now().timestamp())}",
                status=DossierStatus.A_ANALYSER,
                created_by=rh,
                safety_manager=juriste,
                date_of_incident=timezone.now().date(),    # <<< ADD THIS
                title="Chute",
                description="Dans les escaliers",
                location="Siège social, Paris",
                entreprise={
                    'siret': '12345678900001',
                    'raisonSociale': 'Entreprise Alpha',
                    'adresse': '123 Rue de la Paix, Paris',
                    'numeroRisque': '123AB'
                },
                salarie={
                    'nom': 'Dupont',
                    'prenom': 'Jean',
                    'dateNaissance': '1980-05-15',
                    'numeroSecu': '180057512345678',
                    'adresse': '456 Avenue des Champs, Paris',
                    'horairesTravail': '9h-17h'
                },
                accident={
                    'date': '2024-06-01',
                    'heure': '10:30',
                    'lieu': 'Atelier',
                    'circonstances': "Chute d'un objet lourd",
                    'descriptionLesions': 'Fracture du pied droit'
                },
                temoins=[],
                tiers_implique=None,
                service_sante='Service de Santé au Travail'
            )
            self.stdout.write(self.style.SUCCESS(f"✅ DossierATMP {dossier.reference}"))

            # 4) Contentieux
            content = Contentieux.objects.create(
                dossier_atmp=dossier,
                reference=f"CONT-{int(datetime.now().timestamp())}",
                subject={
                    'title': f"Contentieux {dossier.reference}",
                    'description': f"Initiated after audit of {dossier.reference}"
                },
                status=ContentieuxStatus.DRAFT,
                juridiction_steps={}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Contentieux {content.reference}"))

            # 5) Document
            doc = Document.objects.create(
                contentieux=content,
                uploaded_by=rh,
                document_type=DocumentType.DAT,
                original_name='DAT_Jean_Dupont.pdf',
                mime_type='application/pdf',
                size=500_000
            )
            content.documents.add(doc)
            self.stdout.write(self.style.SUCCESS("✅ Document linked to Contentieux"))

            # 6) Audit
            audit = Audit.objects.create(
                dossier_atmp=dossier,
                auditor=juriste,
                status=AuditStatus.IN_PROGRESS,
                decision=None,
                comments='',
                started_at=timezone.now(),
                completed_at=None
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Audit for {dossier.reference}"))

        self.stdout.write(self.style.SUCCESS("🎉 Data seeding complete!"))
