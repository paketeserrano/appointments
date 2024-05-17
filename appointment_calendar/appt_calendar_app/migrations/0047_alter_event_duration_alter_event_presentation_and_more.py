# Generated by Django 4.2.10 on 2024-05-15 13:55

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0046_userworkimageupload'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='duration',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='event',
            name='presentation',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='event',
            name='price',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(0.01)]),
        ),
        migrations.CreateModel(
            name='AppointmentCancellation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancellation_time', models.DateTimeField()),
                ('cancel_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('appointment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation', to='appt_calendar_app.appointment')),
                ('cancelled_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='appt_calendar_app.customuser')),
            ],
        ),
    ]
