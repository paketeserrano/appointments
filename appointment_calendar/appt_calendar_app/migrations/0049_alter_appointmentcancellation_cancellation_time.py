# Generated by Django 4.2.10 on 2024-05-15 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0048_alter_appointmentcancellation_cancellation_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointmentcancellation',
            name='cancellation_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
