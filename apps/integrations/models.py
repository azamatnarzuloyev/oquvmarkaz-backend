import uuid
from django.db import models
from django.conf import settings


class WebhookToken(models.Model):
    """Reklama platformasi uchun webhook URL tokeni."""

    class Platform(models.TextChoices):
        INSTAGRAM = 'instagram', 'Instagram'
        TELEGRAM  = 'telegram',  'Telegram'
        FACEBOOK  = 'facebook',  'Facebook'
        WEBSITE   = 'website',   'Sayt formi'
        OTHER     = 'other',     'Boshqa'

    name       = models.CharField(max_length=100, verbose_name='Nom (masalan: Instagram stories)')
    token      = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    platform   = models.CharField(max_length=20, choices=Platform.choices, default=Platform.OTHER)
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='webhook_tokens',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Webhook token'
        verbose_name_plural = 'Webhook tokenlar'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_platform_display()})'


class InstagramActivity(models.Model):
    """Instagram comment/DM loglari."""

    class EventType(models.TextChoices):
        COMMENT = 'comment', 'Comment'
        DM      = 'dm',      'Direct Message'

    class Status(models.TextChoices):
        REPLIED     = 'replied',     'Javob berildi'
        DM_SENT     = 'dm_sent',     'DM yuborildi'
        LEAD_CREATED = 'lead_created', 'Lead yaratildi'
        FAILED      = 'failed',      'Xato'

    event_type    = models.CharField(max_length=10, choices=EventType.choices)
    sender_id     = models.CharField(max_length=50, blank=True)
    sender_name   = models.CharField(max_length=100, blank=True)
    message_text  = models.TextField(blank=True)
    ai_reply      = models.TextField(blank=True)
    status        = models.CharField(max_length=20, choices=Status.choices)
    lead          = models.ForeignKey(
        'leads.Lead',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='instagram_activities',
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Instagram faoliyat'
        verbose_name_plural = 'Instagram faoliyatlar'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.get_event_type_display()} — {self.sender_name or self.sender_id}'


class AdStat(models.Model):
    """Har kunlik reklama statistikasi (impressions + clicks)."""

    webhook    = models.ForeignKey(WebhookToken, on_delete=models.CASCADE, related_name='stats')
    date       = models.DateField()
    impressions = models.PositiveIntegerField(default=0)
    clicks     = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Reklama statistikasi'
        verbose_name_plural = 'Reklama statistikasi'
        unique_together     = ('webhook', 'date')
        ordering            = ['-date']

    def __str__(self):
        return f'{self.webhook.name} — {self.date}'
