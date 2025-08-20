# your_app/templatetags/hasattr_tags.py
from django import template

register = template.Library()

@register.filter
def has_attr(obj, attr_name):
    return hasattr(obj, attr_name)