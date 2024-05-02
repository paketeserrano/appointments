from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

def custom_user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<account_id>/header_image_<filename>
    return f'user_profiles/{instance.id}/profile_{filename}'

class CustomUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to=custom_user_directory_path, blank=True, null=True, default='user_profiles/placeholder.jpg')
    presentation = models.CharField(max_length=150)
    experience = models.CharField(max_length=2000)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        CustomUser.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.customuser.save()

class Address(models.Model):
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=50)
    province = models.CharField(max_length=50)
    country = models.CharField(max_length=50)

class Account(models.Model):
    admins = models.ManyToManyField(CustomUser, related_name='account_admins_set')
    name = models.CharField(max_length = 120)
    description = models.CharField(max_length = 320)
    account_workers = models.ManyToManyField(CustomUser)
    time_slot_duration = models.IntegerField(default=30) 
    address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='account', null=True)

    def __str__(this):
        return this.name  
    
def account_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<account_id>/header_image_<filename>
    return f'businesses/{instance.business.id}/header_image_{filename}'
    
class AccountUI(models.Model):
    business = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='ui')
    is_visible = models.BooleanField(default=True)
    header_image = models.ImageField(upload_to=account_directory_path, blank=True, null=True, default='businesses/placeholder.jpg')
    description = models.CharField(max_length=500)

    def __str__(self):
        return f'UI for {self.business.name} with path: {self.header_image}'

class Invitee(models.Model):
    email = models.EmailField(max_length = 240)
    name = models.CharField(max_length = 120)
    phone_number = models.CharField(max_length = 15, blank=True, null=True)

    def __str__(this):
        return this.name

class Event(models.Model):
    name = models.CharField(max_length = 120)
    presentation = models.CharField(max_length = 150, default='')
    description = models.CharField(max_length = 2000, default='')
    duration = models.IntegerField()
    event_workers = models.ManyToManyField(CustomUser)
    # This field should contain the different locations options setup by the user
    #location = models.CharField(max_length = 120)
    account = models.ForeignKey(Account, on_delete = models.CASCADE)
    active = models.BooleanField(default=False)
    price = models.FloatField()

    def __str__(this):
        return this.name 
    
def event_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<event_id>/profile_<filename>
    return f'events/{instance.event.id}/profile_{filename}'

class EventUI(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='ui')
    is_visible = models.BooleanField(default=True)
    image = models.ImageField(upload_to=event_directory_path, blank=True, null=True, default='events/placeholder.jpg')

    def __str__(self):
        return f'UI for {self.event.name} with path: {self.image}'

def event_uploads_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/events/<event_id>/uploads/<filename>
    return f'events/{instance.event.id}/uploads/{filename}'

class BusinessEventImageUpload(models.Model):
    account = models.ForeignKey(Account, on_delete = models.CASCADE, related_name='photos')
    event = models.ForeignKey(Event, on_delete = models.CASCADE, related_name='photos')
    upload_date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to=event_uploads_directory_path, blank=True, null=True, default='events/placeholder.jpg')
    
APPOINTMENT_STATUS = [
    ("ACTIVE", "ACTIVE"),
    ("CANCELLED", "CANCELLED"),
]

class Appointment(models.Model):
    invitees = models.ManyToManyField(Invitee)
    date = models.DateField()
    time = models.TimeField()
    event = models.ForeignKey(Event, on_delete = models.CASCADE)
    location = models.CharField(max_length = 120)
    worker = models.ForeignKey(CustomUser, on_delete = models.CASCADE)
    status = models.CharField(max_length = 40, choices = APPOINTMENT_STATUS, default='ACTIVE')    

    def __str__(this):
        return f"Appt scheduled"
    
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
        return self.get_weekday_display()

class SpecialDay(models.Model):
    account = models.ForeignKey(Account, on_delete = models.CASCADE)
    date = models.DateField()
    closed = models.BooleanField(default=True)
    from_hour = models.TimeField()
    to_hour = models.TimeField()

    def __str__(self):
        return str(self.date)
    
