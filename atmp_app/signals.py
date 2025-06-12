# /home/siisi/atmp/atmp_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.conf import settings
from .models import ATMPIncident


@receiver(post_save, sender=ATMPIncident)
def notify_syndic(sender, instance, created, **kwargs):
    if created:
        subject = f"New ATMP Incident: {instance.title}"
        message = f"""
        New incident reported by {instance.provider.get_full_name()} ({instance.provider.email})
        
        Details:
        Title: {instance.title}
        Date: {instance.date_of_incident}
        Location: {instance.location}
        Description: {instance.description}
        
        Please review at: http://yourdomain.com/admin/atmp/atmpincident/{instance.id}/
        """

        # Collect recipients
        recipients = []

        if instance.safety_manager and instance.safety_manager.email:
            recipients.append(instance.safety_manager.email)

        if instance.provider and instance.provider.email:
            recipients.append(instance.provider.email)

        # Add any static emails if needed
        recipients.extend(['medusadbt@gmail.com', 'realcopromanager@gmail.com'])

        # Send email using EmailMessage with BCC
        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,    # MUST match your EMAIL_HOST_USER
            to=[settings.DEFAULT_FROM_EMAIL],  # Can be yourself, to satisfy Gmail
            bcc=recipients,              # Actual recipients hidden
        )
        email.send(fail_silently=False)

        print("Sending email to (BCC):", recipients)
