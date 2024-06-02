import ast
from django import template

register = template.Library()

@register.filter
def widget_type(field):
    return field.field.widget.__class__.__name__.lower()

@register.filter
def parse_list(value):
    try:
        print(f'----------------->Type: {type(value)}')
        parsed_value = ast.literal_eval(value)
        if isinstance(parsed_value, list):
            for item in parsed_value:
                print(item)
            print('It is a list')
            return parsed_value
    except (ValueError, SyntaxError):
        pass
    # If not, return the original value
    return value

@register.filter
def is_list(value):
    return isinstance(value, list)