# /home/siisi/atmp/atmp_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.conf import settings
from .models import DossierATMP


@receiver(post_save, sender=DossierATMP)
def notify_syndic(sender, instance, created, **kwargs):
    if created:
        subject = f"New ATMP Incident: {instance.title}"
        message = f"""
        New incident reported by {instance.created_by.get_full_name()} ({instance.created_by.email})
        
        Details:
        Title: {instance.title}
        Date: {instance.date_of_incident}
        Location: {instance.location}
        Description: {instance.description}
        ADMIN, Please review at: http://atmp.siisi.online/admin/atmp_app/dossieratmp/{instance.id}
        HTML, Please review at: http://atmp.siisi.online/atmp_app/incidents/{instance.id}
        API, Please review at: http://atmp.siisi.online/atmp/api/dossiers/{instance.id}/
        """

        # Collect recipients
        recipients = []

        if instance.safety_manager and instance.safety_manager.email:
            recipients.append(instance.safety_manager.email)

        if instance.created_by and instance.created_by.email:
            recipients.append(instance.created_by.email)

        # Add any static emails if needed
        recipients.extend(['medusadbt@gmail.com', 'charikajadida@gmail.com'])

        # Send email using EmailMessage with BCC
        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,    # MUST match your EMAIL_HOST_USER
            to=[settings.DEFAULT_FROM_EMAIL],  # Can be yourself, to satisfy Gmail
            bcc=recipients,              # Actual recipients hidden
        )
        email.send(fail_silently=False)
