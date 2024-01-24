from django import template
from django.conf import settings

register = template.Library()


@register.filter
def get_dict_attr(obj, attr):
    return obj.get(attr, None)

@register.simple_tag
def get_settings_attr(attr):
    return getattr(settings, attr, "")
