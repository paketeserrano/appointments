# Generated by Django 4.2.10 on 2024-03-16 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0004_invitee_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='admins',
            field=models.ManyToManyField(related_name='account_admins_set', to='appt_calendar_app.customuser'),
        ),
    ]
