# Generated by Django 4.2.10 on 2024-05-02 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0023_alter_businessappearance_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businessappearance',
            name='account',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='appearance', to='appt_calendar_app.account'),
        ),
    ]