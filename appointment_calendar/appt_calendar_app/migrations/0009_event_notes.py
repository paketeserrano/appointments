# Generated by Django 4.2.10 on 2024-06-03 11:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0008_alter_appointmentquestionresponse_appointment'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='notes',
            field=models.CharField(default='', max_length=500),
        ),
    ]
