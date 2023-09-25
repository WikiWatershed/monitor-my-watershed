from django import template

register = template.Library()


@register.filter
def get_dict_attr(obj, attr):
    return obj[attr]
