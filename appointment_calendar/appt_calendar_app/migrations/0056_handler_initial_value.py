from django.db import migrations
from ..libs import utils
def generate_unique_handlers(apps, schema_editor):
    Account = apps.get_model('appt_calendar_app', 'Account')
    for account in Account.objects.all():
        account.handler = utils.generate_unique_handler(Account, account.name)
        account.save()

class Migration(migrations.Migration):

    dependencies = [
        ('appt_calendar_app', '0055_account_handler'),
    ]

    operations = [
        migrations.RunPython(generate_unique_handlers),
    ]