from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0002_instagramactivity'),
        ('leads', '0005_alter_lead_id_alter_leadactivity_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.BigIntegerField()),
                ('username', models.CharField(blank=True, max_length=100)),
                ('full_name', models.CharField(blank=True, max_length=150)),
                ('message_text', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('status', models.CharField(
                    choices=[
                        ('waiting', 'Telefon kutilmoqda'),
                        ('lead_created', 'Lead yaratildi'),
                        ('duplicate', 'Takroriy lead'),
                        ('failed', 'Xato'),
                    ],
                    default='waiting',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lead', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='telegram_activities',
                    to='leads.lead',
                )),
            ],
            options={
                'verbose_name': 'Telegram faoliyat',
                'verbose_name_plural': 'Telegram faoliyatlar',
                'ordering': ['-created_at'],
            },
        ),
    ]
