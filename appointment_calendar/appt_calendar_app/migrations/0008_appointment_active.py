# Generated by Django 4.2.10 on 2024-04-17 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0007_event_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]
