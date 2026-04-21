import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom (masalan: Instagram stories)')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('platform', models.CharField(
                    choices=[
                        ('instagram', 'Instagram'), ('telegram', 'Telegram'),
                        ('facebook', 'Facebook'), ('website', 'Sayt formi'), ('other', 'Boshqa'),
                    ],
                    default='other', max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='webhook_tokens', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Webhook token',
                'verbose_name_plural': 'Webhook tokenlar',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AdStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('impressions', models.PositiveIntegerField(default=0)),
                ('clicks', models.PositiveIntegerField(default=0)),
                ('webhook', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='stats', to='integrations.webhooktoken',
                )),
            ],
            options={
                'verbose_name': 'Reklama statistikasi',
                'verbose_name_plural': 'Reklama statistikasi',
                'ordering': ['-date'],
                'unique_together': {('webhook', 'date')},
            },
        ),
    ]
