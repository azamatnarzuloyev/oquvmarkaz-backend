from django.db import models
from django.conf import settings


class LeadSource(models.TextChoices):
    INSTAGRAM = 'instagram', 'Instagram'
    TELEGRAM  = 'telegram',  'Telegram'
    REFERRAL  = 'referral',  'Tavsiya'
    WEBSITE   = 'website',   'Sayt'
    OTHER     = 'other',     'Boshqa'


class LeadStatus(models.TextChoices):
    NEW         = 'new',         'Yangi'
    NO_ANSWER   = 'no_answer',   "Bog'lanib bo'lmadi"
    THINKING    = 'thinking',    "O'ylayapti"
    TRIAL       = 'trial',       'Sinov darsida'
    CONVERTED   = 'converted',   "To'lov qildi"
    LOST        = 'lost',        "Yo'qotildi"


class Lead(models.Model):
    full_name    = models.CharField(max_length=100, verbose_name='Ism familiya')
    phone        = models.CharField(max_length=13, verbose_name='Telefon')
    source       = models.CharField(max_length=20, choices=LeadSource.choices, default=LeadSource.OTHER, verbose_name='Manba')
    status       = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW, verbose_name='Holat')
    assigned_to  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_leads',
        verbose_name='Mas\'ul xodim',
    )
    notes        = models.TextField(blank=True, verbose_name='Izoh')
    trial_date   = models.DateField(null=True, blank=True, verbose_name='Sinov dars sanasi')
    lost_reason  = models.CharField(max_length=255, blank=True, verbose_name='Yo\'qotish sababi')
    converted_at = models.DateTimeField(null=True, blank=True, verbose_name='Talabaga aylangan vaqt')
    webhook_token = models.ForeignKey(
        'integrations.WebhookToken',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='leads',
        verbose_name='Webhook (reklama)',
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lid'
        verbose_name_plural = 'Lidlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.full_name} — {self.get_status_display()}'


class ActivityType(models.TextChoices):
    CALL           = 'call',           "Qo'ng'iroq"
    NOTE           = 'note',           'Eslatma'
    STATUS_CHANGED = 'status_changed', 'Holat o\'zgartirildi'
    SMS_SENT       = 'sms_sent',       'SMS yuborildi'


class LeadActivity(models.Model):
    lead       = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='lead_activities',
    )
    type       = models.CharField(max_length=30, choices=ActivityType.choices)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Faoliyat'
        verbose_name_plural = 'Faoliyatlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.lead.full_name} — {self.get_type_display()}'
