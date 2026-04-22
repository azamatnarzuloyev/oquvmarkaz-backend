from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
        ('leads', '0005_alter_lead_id_alter_leadactivity_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstagramActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(
                    choices=[('comment', 'Comment'), ('dm', 'Direct Message')],
                    max_length=10,
                )),
                ('sender_id', models.CharField(blank=True, max_length=50)),
                ('sender_name', models.CharField(blank=True, max_length=100)),
                ('message_text', models.TextField(blank=True)),
                ('ai_reply', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('replied', 'Javob berildi'),
                        ('dm_sent', 'DM yuborildi'),
                        ('lead_created', 'Lead yaratildi'),
                        ('failed', 'Xato'),
                    ],
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lead', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='instagram_activities',
                    to='leads.lead',
                )),
            ],
            options={
                'verbose_name': 'Instagram faoliyat',
                'verbose_name_plural': 'Instagram faoliyatlar',
                'ordering': ['-created_at'],
            },
        ),
    ]
