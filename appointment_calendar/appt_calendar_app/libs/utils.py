import re
import random
import string

def generate_unique_handler(model, name_value):
    # Trim and replace spaces with hyphens
    handler = re.sub(r'\s+', '-', name_value.strip()).lower()

    # Check if the handler is unique
    while model.objects.filter(handler=handler).exists():
        # If not unique, add a random string at the end
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        handler = f"{handler}-{random_suffix}"
    
    return handler