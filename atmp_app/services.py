# /home/siisi/atmp/atmp_app/services.py

from.models import Audit, DossierATMP, Contentieux, ContentieuxStatus
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ContentieuxService:
    @staticmethod
    def get_all_contentieux(query_params):
        # Implement pagination/filtering based on query_params if needed
        # For now, a simple find all
        contentieux = Contentieux.objects.all().order_by('-created_at')
        return list(contentieux)

    @staticmethod
    def get_contentieux_by_id(contentieux_id):
        try:
            contentieux = Contentieux.objects.get(id=contentieux_id)
            return contentieux
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def create_from_audit(audit: Audit, dossier: DossierATMP):
        """
        Creates a new Contentieux dossier based on a finalized Audit.
        """
        try:
            # Generate a simple reference for the contentieux
            # The model's save method will also generate one if not provided,
            # but providing a prefix here can be useful for human readability.
            reference = f"CONT-{int(datetime.now().timestamp())}"

            new_contentieux = Contentieux(
                dossier_atmp=dossier, # Link to the DossierATMP instance
                reference=reference,
                subject={
                    "title": f"Contentieux pour dossier {dossier.reference}",
                    "description": f"Contentieux initié suite à l'audit du dossier AT/MP {dossier.reference}."
                },
                status=ContentieuxStatus.DRAFT.value, # Set initial status
                juridiction_steps={}, # Default empty map
                # documents and actions are ManyToMany, add them after saving
            )
            new_contentieux.save()

            # Update the parent DossierATMP with the new contentieux link
            # Since DossierATMP has a OneToOneField to Contentieux, this is handled automatically
            # by the reverse relation `dossier.contentieux_detail = new_contentieux`
            # or simply by the creation of Contentieux with dossier_atmp=dossier.
            # No explicit update needed on DossierATMP if OneToOneField is used correctly.

            logger.info(f"Contentieux {new_contentieux.id} created from audit {audit.id}")
            return new_contentieux
        except Exception as e:
            logger.error(f"Error creating contentieux from audit: {e}")
            raise
