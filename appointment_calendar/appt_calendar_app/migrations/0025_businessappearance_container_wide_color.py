# Generated by Django 4.2.10 on 2024-05-02 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0024_alter_businessappearance_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessappearance',
            name='container_wide_color',
            field=models.CharField(default='#defdef', help_text='Stores the color of the background as a hex code.', max_length=7),
        ),
    ]
