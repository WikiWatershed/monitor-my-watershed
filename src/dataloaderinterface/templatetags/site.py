from django import template
import re
from django.template.defaultfilters import date as date_filter
from datetime import date
from dataloaderinterface.models import SiteRegistration

register = template.Library()


@register.filter(name='get_site_sensor')
def get_site_sensor(site, variable_code):
    if not isinstance(site, SiteRegistration) or not site.status_sensors:
        return

    return next((sensor for sensor in site.status_sensors if sensor.sensor_output.variable_code==variable_code), None)


@register.filter(name='can_administer_site')
def can_administer_site():
    pass
    # return DeviceRegistration.objects.filter(deployment_sampling_feature_uuid__exact=sampling_feature.sampling_feature_uuid).first()


@register.filter(name='add_input_class', is_safe=True)
def add_input_class(value, arg):
    if re.search(r'class', value, re.IGNORECASE):
        return re.sub(r'(class=")', r'\1{0} '.format(arg), value)
    else:
        return re.sub(r'(<input)', r'\1 class="{0}"'.format(arg), value)


@register.filter("roundfloat")
def round_float(value, argv):
    if isinstance(value, float):
        round_to = 1
        if argv is not None and isinstance(argv, int):
            round_to = argv
        return round(value, round_to)
    else:
        return value


@register.filter(name='abs')
def abs_filter(value):
    return abs(value)


@register.filter(name='to_string')
def to_string(value):
    return '{0:g}'.format(value)


@register.filter("divide")
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter("date_format")
def date_format(value, arg):
    if value is None:
        return ''

    if isinstance(value, date):
        return date_filter(value, arg=arg)

    return str(value)


@register.filter("get_csv_sensors_parameters")
def get_csv_sensors_parameters(sensors):
    return '&'.join(["result_id={id}".format(id=sensor.result_id) for sensor in sensors])
