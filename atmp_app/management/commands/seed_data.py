# atmp_app/management/commands/seed_data.py

from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q # Import Q for complex queries
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
            # 1) Selective wipe existing seed data
            # The most robust way for development is to delete users by the pattern they use.
            # This handles cases where 'is_seeded' might not have been set on previous runs or manual creations.
            seeded_user_email_pattern = '@example.com'
            users_to_delete_by_email_pattern = User.objects.filter(email__endswith=seeded_user_email_pattern)

            # Important: Get the IDs *before* deleting anything to ensure querysets aren't affected
            users_to_delete_ids = list(users_to_delete_by_email_pattern.values_list('id', flat=True))


            self.stdout.write("🗑️  Clearing old seed data related to '@example.com' users...")

            # A) Delete Documents uploaded by these users
            # Ensure related objects are deleted first if they depend on users
            Document.objects.filter(uploaded_by__in=users_to_delete_by_email_pattern).delete()
            self.stdout.write("🗑️  Cleared documents uploaded by previous seed users.")

            # B) Identify DossierATMP objects created by or assigned to these users
            # Deleting DossierATMP will cascade to Contentieux, Audit, Temoin, and Tiers
            dossiers_to_delete = DossierATMP.objects.filter(
                Q(created_by__in=users_to_delete_by_email_pattern) |
                Q(safety_manager__in=users_to_delete_by_email_pattern)
            )
            count_dossiers_deleted = dossiers_to_delete.count()
            if count_dossiers_deleted > 0:
                dossiers_to_delete.delete()
                self.stdout.write(f"🗑️  Cleared {count_dossiers_deleted} DossierATMP objects and their related data.")
            else:
                self.stdout.write("🗑️  No DossierATMP objects linked to previous seed users found.")

            # C) Delete all Action objects (as they are not directly linked to specific users in the seed data)
            # If Actions could be created by non-seeded users, this would need refinement.
            Action.objects.all().delete()
            self.stdout.write("🗑️  Cleared all Action objects.")

            # D) Finally, delete the users themselves based on the email pattern
            count_users_deleted = users_to_delete_by_email_pattern.count()
            if count_users_deleted > 0:
                users_to_delete_by_email_pattern.delete()
                self.stdout.write(f"🗑️  Cleared {count_users_deleted} previous seed users ('@example.com').")
            else:
                self.stdout.write("🗑️  No previous seed users ('@example.com') found to clear.")

            self.stdout.write("🗑️  Old seed data cleared selectively.")

            # 2) Create users (this part remains the same, but now it will succeed)
            admin = User.objects.create_user(
                email='admin@example.com',
                password='secret',
                name='Admin User',
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_seeded=True # Mark as seeded
            )
            juriste = User.objects.create_user(
                email='juriste@example.com',
                password='juriste123',
                name='Juriste Alpha',
                role=UserRole.JURISTE,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            rh = User.objects.create_user(
                email='rh@example.com',
                password='rh123',
                name='RH Beta',
                role=UserRole.RH,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            safety_manager = User.objects.create_user(
                email='safety@example.com',
                password='safety123',
                name='Safety Manager Gamma',
                role=UserRole.SAFETY_MANAGER,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            manager = User.objects.create_user(
                email='manager@example.com',
                password='manager123',
                name='Manager Charlie',
                role=UserRole.MANAGER,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            qse = User.objects.create_user(
                email='qse@example.com',
                password='qse123',
                name='QSE David',
                role=UserRole.QSE,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            direction = User.objects.create_user(
                email='direction@example.com',
                password='direction123',
                name='Direction Eric',
                role=UserRole.DIRECTION,
                is_staff=True,
                is_seeded=True # Mark as seeded
            )
            employee = User.objects.create_user(
                email='employee@example.com',
                password='employee123',
                name='Employee Delta',
                role=UserRole.EMPLOYEE,
                is_staff=False,
                is_seeded=True # Mark as seeded
            )
            self.stdout.write(self.style.SUCCESS("✅ Users created for all roles"))

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