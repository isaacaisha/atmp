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
    Temoin,
    Tiers
)
from users.models import CustomUser as User, UserRole


class Command(BaseCommand):
    help = 'Seeds the database with initial data for testing and development.'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting data seeding…")

        with transaction.atomic():
            # 1) wipe existing data
            Temoin.objects.all().delete()
            Tiers.objects.all().delete()
            Audit.objects.all().delete()
            Contentieux.objects.all().delete()
            DossierATMP.objects.all().delete()
            Document.objects.all().delete()
            Action.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write("🗑️  Cleared old rows")

            # 2) Create users
            admin = User.objects.create_user(
                email='admin@example.com',
                password='secret',
                name='Admin User',
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True
            )
            # FIX: Change UserRole.JURIST to UserRole.JURISTE
            juriste = User.objects.create_user(
                email='juriste@example.com',
                password='juriste123',
                name='Juriste Alpha',
                role=UserRole.JURISTE # <-- Corrected: Use JURISTE
            )
            rh = User.objects.create_user(
                email='rh@example.com',
                password='rh123',
                name='RH Beta',
                role=UserRole.RH
            )
            safety_manager = User.objects.create_user(
                email='safety@example.com',
                password='safety123',
                name='Safety Manager Gamma',
                role=UserRole.SAFETY_MANAGER
            )
            employee = User.objects.create_user(
                email='employee@example.com',
                password='employee123',
                name='Employee Delta',
                role=UserRole.EMPLOYEE
            )
            self.stdout.write(self.style.SUCCESS("✅ Users created"))

            # 3) Dossier ATMP
            dossier = DossierATMP.objects.create(
                status=DossierStatus.A_ANALYSER,
                created_by=employee,
                safety_manager=safety_manager,
                date_of_incident=timezone.now().date(),
                title="Chute",
                description="Dans les escaliers",
                location="Siège social, Paris",
                entreprise={
                    'name': 'Entreprise Alpha',
                    'siret': '12345678900001',
                    'address': '123 Rue de la Paix, Paris',
                    'numeroRisque': '123AB'
                },
                salarie={
                    'first_name': 'Jean',
                    'last_name': 'Dupont',
                    'social_security_number': '180057512345678',
                    'date_of_birth': '1980-05-15',
                    'job_title': 'Technicien'
                },
                accident={
                    'date': '2024-06-01',
                    'time': '10:30',
                    'description': "Chute d'un objet lourd, fracture du pied droit",
                    'type_of_accident': 'Chute d\'objet',
                    'detailed_circumstances': "L'employé a chuté en manipulant un objet lourd."
                },
                tiers_implique=None,
                service_sante='Service de Santé au Travail'
            )
            self.stdout.write(self.style.SUCCESS(f"✅ DossierATMP {dossier.reference}"))

            # Create Temoin objects linked to the dossier
            Temoin.objects.create(
                dossier_atmp=dossier,
                nom="Alice Smith",
                coordonnees="alice.s@example.com, 0612345678"
            )
            Temoin.objects.create(
                dossier_atmp=dossier,
                nom="Bob Johnson",
                coordonnees="bob.j@example.com"
            )
            self.stdout.write(self.style.SUCCESS("✅ Temoin objects created and linked to Dossier"))

            # Create Tiers object linked to the dossier
            Tiers.objects.create(
                dossier_atmp=dossier,
                nom="XYZ Company",
                adresse="789 Business Road, Paris",
                assurance="Axa Assurance",
                immatriculation="FR123456789"
            )
            self.stdout.write(self.style.SUCCESS("✅ Tiers object created and linked to Dossier"))

            # 4) Contentieux
            content = Contentieux.objects.create(
                dossier_atmp=dossier,
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
            dossier.documents.add(doc)
            self.stdout.write(self.style.SUCCESS("✅ Document linked to Contentieux and Dossier"))

            # 6) Audit
            audit = Audit.objects.create(
                dossier_atmp=dossier,
                auditor=safety_manager,
                status=AuditStatus.IN_PROGRESS,
                decision=None,
                comments='Initial audit in progress.',
                started_at=timezone.now(),
                completed_at=None
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Audit for {dossier.reference}"))

        self.stdout.write(self.style.SUCCESS("🎉 Data seeding complete!"))
