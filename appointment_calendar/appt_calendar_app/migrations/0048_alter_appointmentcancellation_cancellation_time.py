# Generated by Django 4.2.10 on 2024-05-15 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0047_alter_event_duration_alter_event_presentation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointmentcancellation',
            name='cancellation_time',
            field=models.DateTimeField(blank=True),
        ),
    ]