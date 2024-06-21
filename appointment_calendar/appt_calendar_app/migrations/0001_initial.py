# Generated by Django 4.2.10 on 2024-06-21 10:14

import appt_calendar_app.models
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('presentation', models.CharField(max_length=320)),
                ('time_slot_duration', models.IntegerField(default=30)),
                ('handler', models.SlugField(max_length=255, unique=True)),
                ('default_language', models.CharField(choices=[('en', 'English'), ('es', 'Spanish')], default='es', max_length=7)),
            ],
        ),
        migrations.CreateModel(
            name='AccountUI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_visible', models.BooleanField(default=True)),
                ('header_image', models.ImageField(blank=True, null=True, upload_to=appt_calendar_app.models.account_directory_path)),
                ('description', models.CharField(max_length=500)),
                ('business', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ui', to='appt_calendar_app.account')),
            ],
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=150)),
                ('city', models.CharField(max_length=50)),
                ('province', models.CharField(max_length=50)),
                ('country', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('video_conference', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'ACTIVE'), ('CANCELLED', 'CANCELLED')], default='ACTIVE', max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='Blog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('account_ui', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blogs', to='appt_calendar_app.accountui')),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=100)),
                ('profile_image', models.ImageField(blank=True, null=True, upload_to=appt_calendar_app.models.custom_user_directory_path)),
                ('presentation', models.CharField(max_length=150)),
                ('experience', models.CharField(max_length=2000)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('presentation', models.CharField(default='', max_length=200)),
                ('notes', models.CharField(default='', max_length=500)),
                ('description', models.CharField(default='', max_length=2000)),
                ('duration', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('active', models.BooleanField(default=False)),
                ('price', models.FloatField(validators=[django.core.validators.MinValueValidator(-0.01)])),
                ('handler', models.SlugField(max_length=255, unique=True)),
                ('time_slot_duration', models.IntegerField(default=30)),
                ('video_conference', models.URLField(blank=True, null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='appt_calendar_app.account')),
                ('event_workers', models.ManyToManyField(to='appt_calendar_app.customuser')),
                ('locations', models.ManyToManyField(related_name='events', to='appt_calendar_app.address')),
            ],
        ),
        migrations.CreateModel(
            name='EventPageOptions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='event_page_options', to='appt_calendar_app.event')),
            ],
        ),
        migrations.CreateModel(
            name='UserWorkImageUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('image', models.ImageField(upload_to=appt_calendar_app.models.user_uploads_directory_path)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='appt_calendar_app.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='UserSocialMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('facebook', models.URLField(blank=True, null=True)),
                ('twitter', models.URLField(blank=True, null=True)),
                ('tiktok', models.URLField(blank=True, null=True)),
                ('instagram', models.URLField(blank=True, null=True)),
                ('custom_user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='social_media', to='appt_calendar_app.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='SpecialDay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('closed', models.BooleanField(default=True)),
                ('from_hour', models.TimeField()),
                ('to_hour', models.TimeField()),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appt_calendar_app.account')),
            ],
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_published', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('blog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='appt_calendar_app.blog')),
            ],
        ),
        migrations.CreateModel(
            name='OpenningTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.CharField(choices=[('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')], max_length=40)),
                ('from_hour', models.TimeField()),
                ('to_hour', models.TimeField()),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opening_hours', to='appt_calendar_app.account')),
            ],
        ),
        migrations.CreateModel(
            name='Invitee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=240)),
                ('name', models.CharField(max_length=120)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('accounts', models.ManyToManyField(related_name='invitees', to='appt_calendar_app.account')),
            ],
        ),
        migrations.CreateModel(
            name='EventUI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_visible', models.BooleanField(default=False)),
                ('image', models.ImageField(blank=True, null=True, upload_to=appt_calendar_app.models.event_directory_path)),
                ('description', models.CharField(default='', max_length=2000)),
                ('event', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ui', to='appt_calendar_app.event')),
            ],
        ),
        migrations.CreateModel(
            name='EventPageQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=2000)),
                ('required', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('event_page_options', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='appt_calendar_app.eventpageoptions')),
            ],
        ),
        migrations.CreateModel(
            name='EventPageAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer_type', models.CharField(choices=[('single_line', 'Single Line'), ('multi_line', 'Multiple Lines'), ('checkbox', 'Checkbox'), ('radio', 'Radio Button'), ('dropdown', 'Dropdown')], max_length=50)),
                ('options', models.JSONField(blank=True, null=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='appt_calendar_app.eventpagequestion')),
            ],
        ),
        migrations.CreateModel(
            name='BusinessEventImageUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('image', models.ImageField(blank=True, default='events/placeholder.jpg', null=True, upload_to=appt_calendar_app.models.event_uploads_directory_path)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='appt_calendar_app.account')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='appt_calendar_app.event')),
            ],
        ),
        migrations.CreateModel(
            name='BusinessAppearance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('header_bar_color', models.CharField(default='#8CBDB9', help_text='Color of the header bar.', max_length=7)),
                ('header_bar_font_color', models.CharField(default='#000000', help_text='Font color for text on header bar.', max_length=7)),
                ('background_color', models.CharField(default='#E8ECEB', help_text='Color of the website background.', max_length=7)),
                ('text_color', models.CharField(default='#000000', help_text='Color of the text on the website.', max_length=7)),
                ('section_header_font_color', models.CharField(default='#000000', help_text='Color of the sections header text.', max_length=7)),
                ('service_background_color', models.CharField(default='#2D3E4E', help_text='Color of the service background card.', max_length=7)),
                ('worker_background_color', models.CharField(default='#E09E50', help_text='Color of the worker background card.', max_length=7)),
                ('hero_image_font_color', models.CharField(default='#000000', help_text='Colors for text on main website image', max_length=7)),
                ('main_manu_background_color', models.CharField(default='#8CBDB9', help_text='Background color for main menu', max_length=7)),
                ('main_menu_font_color', models.CharField(default='#000000', help_text='Font color for main menu links', max_length=7)),
                ('main_menu_font_hover_color', models.CharField(default='#FFFFFF', help_text='Font colors for main menu links hover', max_length=7)),
                ('burger_button_background_color', models.CharField(default='#E09E50', help_text='Background color for burger main menu', max_length=7)),
                ('buger_menu_lines_color', models.CharField(default='#E8ECEB', help_text='Burger menu line colors', max_length=7)),
                ('appointment_background_image', models.ImageField(blank=True, null=True, upload_to=appt_calendar_app.models.web_directory_path)),
                ('booking_form_background_color', models.CharField(default='#E8ECEB', help_text='Background color for main form on the booking page', max_length=7)),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='appearance', to='appt_calendar_app.account')),
            ],
        ),
        migrations.CreateModel(
            name='AppointmentQuestionResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response', models.TextField()),
                ('appointment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='appt_calendar_app.appointment')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appt_calendar_app.eventpagequestion')),
            ],
        ),
        migrations.CreateModel(
            name='AppointmentCancellation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancelled_by', models.CharField(max_length=120)),
                ('cancellation_time', models.DateTimeField(blank=True, null=True)),
                ('cancel_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('reason', models.CharField(default='', max_length=250)),
                ('appointment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation', to='appt_calendar_app.appointment')),
            ],
        ),
        migrations.AddField(
            model_name='appointment',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appt_calendar_app.event'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='invitees',
            field=models.ManyToManyField(to='appt_calendar_app.invitee'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='appointments', to='appt_calendar_app.address'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='worker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appt_calendar_app.customuser'),
        ),
        migrations.AddField(
            model_name='account',
            name='account_workers',
            field=models.ManyToManyField(to='appt_calendar_app.customuser'),
        ),
        migrations.AddField(
            model_name='account',
            name='address',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='account', to='appt_calendar_app.address'),
        ),
        migrations.AddField(
            model_name='account',
            name='admins',
            field=models.ManyToManyField(related_name='account_admins_set', to='appt_calendar_app.customuser'),
        ),
        migrations.CreateModel(
            name='AccountInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accepted', models.BooleanField(default=False)),
                ('accepted_on', models.DateTimeField(blank=True, null=True)),
                ('recipient_email', models.EmailField(max_length=240)),
                ('recipient_name', models.CharField(max_length=100)),
                ('notes', models.CharField(max_length=500)),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='appt_calendar_app.account')),
            ],
            options={
                'unique_together': {('business', 'recipient_email')},
            },
        ),
    ]
