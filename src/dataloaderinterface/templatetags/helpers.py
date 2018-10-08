from datetime import datetime, time, timedelta
from django import template
from django.utils.timesince import timesince
from django.utils.formats import date_format

register = template.Library()


@register.filter("utc_timesince", is_safe=False)
def timesince_filter(value):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    if not value:
        return ''
    try:
        return timesince(value, datetime.utcnow())
    except (ValueError, TypeError, AttributeError):
        return ''


@register.filter("replace_hour")
def replace_hour(value, argv):
    if not value:
        return ''

    if isinstance(value, datetime):
        return datetime.combine(value.date(), time(hour=5, minute=0))
    else:
        return ''


@register.filter("is_stale")
def is_stale(value, default):
    if not value:
        return ''

    try:
        if default > 0:
            return (datetime.utcnow() - value) > timedelta(hours=default.hours_threshold.total_seconds()/3600)
        return (datetime.utcnow() - value) > timedelta(hours=72)
    except AttributeError:
        return ''


@register.filter
def divide(value, arg):
    try:
        return int(value) / int(arg) if int(arg) != 0 else 0
    except (ValueError, ZeroDivisionError):
        return None


@register.filter("data_age")
def data_age(value):
    if not value:
        return 'red'

    val = datetime.utcnow() - value

    if val < timedelta(hours=6):
        return "darkgreen"
    elif val < timedelta(hours=72):
        return "lightgreen"
    elif val < timedelta(hours=336):
        return "yellow"
    else:
        return "red"
