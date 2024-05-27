from django.db import migrations
from ..libs import utils
def generate_unique_handlers(apps, schema_editor):
    Event = apps.get_model('appt_calendar_app', 'Event')
    for event in Event.objects.all():
        event.handler = utils.generate_unique_handler(Event, event.name)
        event.save()

class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0058_event_handler'),
    ]

    operations = [
        migrations.RunPython(generate_unique_handlers),
    ]