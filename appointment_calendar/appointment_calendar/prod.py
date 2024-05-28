from .settings import *

# Using dev defaults for now but the settings will change to the commented ones in prod once I understand them
DEBUG = False
ALLOWED_HOSTS = ['*']

# Ensure you have the following configurations for security
if not DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'


#DEBUG = False
#ALLOWED_HOSTS = ['your_domain_or_ip']
