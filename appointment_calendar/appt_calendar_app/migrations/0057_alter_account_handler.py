# Generated by Django 4.2.10 on 2024-05-24 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0056_handler_initial_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='handler',
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
    ]
