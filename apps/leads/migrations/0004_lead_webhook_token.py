from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
        ('leads', '0003_add_no_answer_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='webhook_token',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='leads',
                to='integrations.webhooktoken',
                verbose_name='Webhook (reklama)',
            ),
        ),
    ]
