from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lead, LeadStatus


@receiver(post_save, sender=Lead)
def lead_post_save(sender, instance, created, **kwargs):
    if created:
        from apps.notifications.tasks import send_welcome_sms
        parts = instance.full_name.strip().split()
        name = parts[0] if parts else 'Mehmon'
        send_welcome_sms.delay(phone=instance.phone, name=name)
