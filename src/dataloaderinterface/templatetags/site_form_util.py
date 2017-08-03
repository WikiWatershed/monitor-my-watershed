from django import template

register = template.Library()


@register.filter(name='get_field_data')
def get_field_data(form, field_name):
    return form[field_name].field.to_python(form[field_name].data) or form[field_name].initial


@register.filter(name='has_data')
def has_data(form):
    return len(form.changed_data) or len(form.initial)


@register.filter(name='is_deleted')
def is_deleted(form):
    return 'DELETE' in form.changed_data
