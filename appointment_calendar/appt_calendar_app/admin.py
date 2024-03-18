from django.contrib import admin
from .models import Account, Event, Invitee, Appointment, CustomUser, OpenningTime, SpecialDay

# Register your models here.
admin.site.register(Account)
admin.site.register(Event)
admin.site.register(Invitee)
admin.site.register(Appointment)
admin.site.register(CustomUser)
admin.site.register(OpenningTime)
admin.site.register(SpecialDay)