# Generated by Django 4.2.10 on 2024-05-16 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0050_alter_appointmentcancellation_cancelled_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointmentcancellation',
            name='reason',
            field=models.CharField(default='', max_length=250),
        ),
    ]