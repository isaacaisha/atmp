# /home/siisi/atmp/atmp_app/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.conf import settings
from .models import DossierATMP
from .models import DossierATMP
from django.urls import reverse
from django.contrib.sites.models import Site


@receiver(post_save, sender=DossierATMP)
def notify_syndic(sender, instance, created, **kwargs):
    if created:
        subject = f"New ATMP Incident: {instance.title}"
        
        # Get the current domain. This is generally preferred over hardcoding.
        # Requires 'django.contrib.sites' app in INSTALLED_APPS
        # and a Site object configured in Django Admin (e.g., example.com -> atmp.siisi.online)
        current_site = Site.objects.get_current()
        # Ensure your SITE_ID in settings.py points to the correct site object.
        # In production, this should be your HTTPS domain.
        base_url = f"https://{current_site.domain}"

        # Using reverse for more robust URL generation, combine with base_url
        admin_url = reverse('admin:atmp_app_dossieratmp_change', args=[instance.id])
        html_url = reverse('atmp_app:incident-detail', args=[instance.id])
        api_url = reverse('atmp_app:dossier-detail', args=[instance.id])  # Using DRF named URL

        message = f"""
        New incident reported by {instance.created_by.get_full_name()} ({instance.created_by.email})
        
        Details:
        Title: {instance.title}
        Date: {instance.date_of_incident}
        Location: {instance.location}
        Description: {instance.description}
        ADMIN, Please review at: {base_url}{admin_url}
        HTML, Please review at: {base_url}{html_url}
        API, Please review at: {base_url}{api_url}
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
