from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.core.validators import MinValueValidator
from django.dispatch import receiver
from django.utils import timezone
import uuid
import os
from .libs import utils


# Create your models here.

def custom_user_directory_path(instance, filename):
    return f'user_profiles/{instance.id}/profile_{filename}'

class CustomUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to=custom_user_directory_path, blank=True, null=True)
    presentation = models.CharField(max_length=150)
    experience = models.CharField(max_length=2000)

    def __str__(self):
        return self.user.username
    
def user_uploads_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_profiles/<custom_user_id>/uploads/<filename>
    return f'user_profiles/{instance.user.id}/uploads/{filename}'

class UserWorkImageUpload(models.Model):
    user = models.ForeignKey(CustomUser, on_delete = models.CASCADE, related_name='photos')
    upload_date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to=user_uploads_directory_path)

class UserSocialMedia(models.Model):
    custom_user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='social_media')
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    tiktok = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)

    def __str__(self):
        return f'Social Media for {self.custom_user.user.username}'
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        custom_user = CustomUser.objects.create(user=instance)
        UserSocialMedia.objects.create(custom_user=custom_user)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.customuser.save()  

class Address(models.Model):
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=50)
    province = models.CharField(max_length=50)
    country = models.CharField(max_length=50)

    def __str__(this):
        return f'{this.address}, {this.city}, {this.province}, {this.country}' 
    
class Account(models.Model):
    admins = models.ManyToManyField(CustomUser, related_name='account_admins_set')
    name = models.CharField(max_length = 120)
    presentation = models.CharField(max_length = 320)
    account_workers = models.ManyToManyField(CustomUser)
    time_slot_duration = models.IntegerField(default=30) 
    address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='account', null=True)
    handler = models.SlugField(max_length=255, unique=True)

    def save(self, *args, **kwargs):
        if not self.handler:
            self.handler = utils.generate_unique_handler(Account, self.name)
        super().save(*args, **kwargs)

    def __str__(this):
        return this.name  
    
class AccountInvitation(models.Model):
    business = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='invitations')
    accepted = models.BooleanField(default=False)
    accepted_on = models.DateTimeField(blank=True, null=True)
    recipient_email = models.EmailField(max_length=240)
    recipient_name = models.CharField(max_length=100)
    notes = models.CharField(max_length=500)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('business', 'recipient_email')

    def __str__(self):
        return f"{self.business.name} - {self.recipient_email}"
    
def account_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<account_id>/header_image_<filename>
    return f'businesses/{instance.business.id}/header_image_{filename}'
    
class AccountUI(models.Model):
    business = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='ui')
    is_visible = models.BooleanField(default=True)
    header_image = models.ImageField(upload_to=account_directory_path, blank=True, null=True)
    description = models.CharField(max_length=500)

    def __str__(self):
        return f'UI for {self.business.name} with path: {self.header_image}'
    
class Invitee(models.Model):
    email = models.EmailField(max_length = 240)
    name = models.CharField(max_length = 120)
    phone_number = models.CharField(max_length = 15, blank=True, null=True)
    accounts = models.ManyToManyField('Account', related_name='invitees')

    def __str__(this):
        return this.name

class Event(models.Model):
    name = models.CharField(max_length = 120)
    presentation = models.CharField(max_length = 200, default='')
    notes = models.CharField(max_length = 500, default='')
    description = models.CharField(max_length = 2000, default='')
    duration = models.IntegerField(validators=[MinValueValidator(1)])
    event_workers = models.ManyToManyField(CustomUser)
    account = models.ForeignKey(Account, on_delete = models.CASCADE, related_name = 'events')
    active = models.BooleanField(default=False)
    price = models.FloatField(validators=[MinValueValidator(-0.01)])
    handler = models.SlugField(max_length=255, unique=True)
    locations = models.ManyToManyField(Address, related_name='events')   
    time_slot_duration = models.IntegerField(default=30)
    video_conference = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.handler:
            self.handler = utils.generate_unique_handler(Event, self.name)
        super().save(*args, **kwargs)

    def __str__(this):
        return this.name 
    
class EventPageOptions(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='event_page_options')

class EventPageQuestion(models.Model):
    event_page_options = models.ForeignKey(EventPageOptions, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=2000)
    required = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.text
    
class EventPageAnswer(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('single_line', 'Single Line'),
        ('multi_line', 'Multiple Lines'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio Button'),
        ('dropdown', 'Dropdown')
    ]

    question = models.ForeignKey(EventPageQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_type = models.CharField(max_length=50, choices=QUESTION_TYPE_CHOICES)
    options = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.question.text} - {self.answer_type}"


def event_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<event_id>/profile_<filename>
    return f'events/{instance.event.id}/profile_{filename}'

class EventUI(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='ui')
    is_visible = models.BooleanField(default=False)
    image = models.ImageField(upload_to=event_directory_path, blank=True, null=True)
    description = models.CharField(max_length = 2000, default='')

    def __str__(self):
        return f'UI for {self.event.name} with path: {self.image}'
    
@receiver(post_delete, sender=EventUI)
def delete_event_ui_image(sender, instance, **kwargs):
    """Deletes image files on `EventUI` object deletion."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

def event_uploads_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<event_id>/uploads/<filename>
    return f'events/{instance.event.id}/uploads/{filename}'

class BusinessEventImageUpload(models.Model):
    account = models.ForeignKey(Account, on_delete = models.CASCADE, related_name='photos')
    event = models.ForeignKey(Event, on_delete = models.CASCADE, related_name='photos')
    upload_date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to=event_uploads_directory_path, blank=True, null=True, default='events/placeholder.jpg')

@receiver(post_delete, sender=BusinessEventImageUpload)
def delete_business_event_image_upload(sender, instance, **kwargs):
    """Deletes image files on `BusinessEventImageUpload` object deletion."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
    
APPOINTMENT_STATUS = [
    ("ACTIVE", "ACTIVE"),
    ("CANCELLED", "CANCELLED"),
]

class Appointment(models.Model):
    invitees = models.ManyToManyField(Invitee)
    date = models.DateField()
    time = models.TimeField()
    event = models.ForeignKey(Event, on_delete = models.CASCADE)
    location = models.ForeignKey('Address', on_delete=models.CASCADE, related_name='appointments', null=True)
    video_conference = models.URLField(blank=True, null=True)
    worker = models.ForeignKey(CustomUser, on_delete = models.CASCADE) # NOTE: on_delete should change to something else because if we delete a worker, the appointment should be kept
    status = models.CharField(max_length = 40, choices = APPOINTMENT_STATUS, default='ACTIVE')    

    def __str__(this):
        return f"Appt scheduled"
    
class AppointmentQuestionResponse(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(EventPageQuestion, on_delete=models.CASCADE)
    response = models.TextField()

    def __str__(self):
        return f"{self.question.text}: {self.response}"

class AppointmentCancellation(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='cancellation')
    cancelled_by = models.CharField(max_length = 120)
    cancellation_time = models.DateTimeField(blank=True, null=True)
    cancel_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reason = models.CharField(max_length = 250, default='')

    def __str__(self):
        return f"Cancellation for {self.appointment}"
    
WEEKDAYS = [
    ("0", "Monday"),
    ("1", "Tuesday"),
    ("2", "Wednesday"),
    ("3", "Thursday"),
    ("4", "Friday"),
    ("5", "Saturday"),
    ("6", "Sunday"),
]

# TODO: Enforce that account and weekday combination are unique
class OpenningTime(models.Model):
    account = models.ForeignKey(Account, on_delete = models.CASCADE, related_name='opening_hours')
    weekday = models.CharField(max_length = 40, choices=WEEKDAYS)
    from_hour = models.TimeField()
    to_hour = models.TimeField()

    def __str__(self):
        return f'{self.get_weekday_display()} - {self.from_hour} to {self.to_hour}'

class SpecialDay(models.Model):
    account = models.ForeignKey(Account, on_delete = models.CASCADE)
    date = models.DateField()
    closed = models.BooleanField(default=True)
    from_hour = models.TimeField()
    to_hour = models.TimeField()

    def __str__(self):
        return str(self.date)
    
def web_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<event_id>/profile_<filename>
    return f'events/{instance.account.id}/{filename}'

class BusinessAppearance(models.Model):
    account = models.OneToOneField(Account, on_delete = models.CASCADE, related_name='appearance')
    header_bar_color = models.CharField(max_length=7, default='#8CBDB9', help_text="Color of the header bar.")
    header_bar_font_color = models.CharField(max_length=7, default='#000000', help_text="Font color for text on header bar.")
    background_color = models.CharField(max_length=7, default='#E8ECEB', help_text="Color of the website background.")
    text_color = models.CharField(max_length=7, default='#000000', help_text="Color of the text on the website.")
    section_header_font_color = models.CharField(max_length=7, default='#000000', help_text="Color of the sections header text.")
    service_background_color = models.CharField(max_length=7, default='#2D3E4E', help_text="Color of the service background card.")
    worker_background_color = models.CharField(max_length=7, default='#E09E50', help_text="Color of the worker background card.")
    hero_image_font_color = models.CharField(max_length=7, default='#000000', help_text="Colors for text on main website image")
    main_manu_background_color = models.CharField(max_length=7, default='#8CBDB9', help_text="Background color for main menu")
    main_menu_font_color = models.CharField(max_length=7, default='#000000', help_text="Font color for main menu links")
    main_menu_font_hover_color = models.CharField(max_length=7, default='#FFFFFF', help_text="Font colors for main menu links hover")  
    burger_button_background_color= models.CharField(max_length=7, default='#E09E50', help_text="Background color for burger main menu")  
    buger_menu_lines_color = models.CharField(max_length=7, default='#E8ECEB', help_text="Burger menu line colors") 
    appointment_background_image = models.ImageField(upload_to=web_directory_path, blank=True, null=True)   
    booking_form_background_color = models.CharField(max_length=7, default='#E8ECEB', help_text="Background color for main form on the booking page") 

    def __str__(self):
        return f"UI Configuration for Header Color {self.header_bar_color}" 
    
