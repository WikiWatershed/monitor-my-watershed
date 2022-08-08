from datetime import datetime
from math import trunc
from typing import Tuple, List
import zoneinfo

# Calculate UTC Offset for a tz & dt
def get_utcoffset(tz_key: str = None, 
                  dt: datetime = None) -> Tuple[int, str, str]:
    '''
    Calculate standard time UTC offset integer, offset timedelta string, 
    and short name for Standard Time for a given IANA timezone key and 
    a given datetime.
    
    tz_key: a valid `zoneinfo` timezone key. 
    If `None` it is based on timezone information from the operating system.

    dt: the datetime used to determine the UTC offset for a given timezone, 
    considering daylight savings vs. standard time. 
    If `None` it is assumed to be January 1st 2022, to return Standard Time in the northern hemisphere
    
    WARNING: This providesConversion from daylight savings to standard time
    will not likely work in the southern hemisphere. 
    '''
    if not dt:
        dt = datetime.now()

    if not tz_key:
        # Get local timezone
        dt_tz = dt.astimezone() 
    else:
        # Get local timezone
        dt_tz = dt.astimezone(zoneinfo.ZoneInfo(tz_key)) 

    
    utc_offset = dt_tz.utcoffset().total_seconds() / (60*60)
    utc_offset_int = trunc(utc_offset)
    
    return utc_offset_int, dt_tz.isoformat()[-6:], dt_tz.tzname()


def make_tz_tuple_list(tz_key_list: list = None,
                       dt: datetime = None) -> list:
    '''
    Creates a list of tuples with:
    - `zoneinfo` timezone keys
    - display field for timezone info, which is a concatenation of:
      - UTC offset in hours
      - `zoneinfo` timezone key
      - `zoneinfo` timezone name/code, which often distinguishes
      daylight savings (D) vs. standard time (S).

    tz_key_list: a supplied list of `zoneinfo` timezone keys.
        If None, then uses all >500 `zoneinfo` timezone keys 
    '''
    tz_tuple_list = []

    if not tz_key_list:
        tz_key_list = zoneinfo.available_timezones()
    else:
        tz_key_list
    
    if not dt:
        dt = datetime.utcnow().astimezone(zoneinfo.ZoneInfo('UTC'))

    for tz_key in tz_key_list:
        tz_info = get_utcoffset(tz_key, dt)
        tz_display = f"(UTC{tz_info[1]}) {tz_key} ({tz_info[2]})"
        tz_tuple = (tz_key, tz_display)
        tz_tuple_list.append(tz_tuple)
    
    def item2(tz_tuple):
        return get_utcoffset(tz_tuple[0])[0]

    tz_tuple_list_sorted = tz_tuple_list.sort(reverse=True, key=item2)
    
    return tz_tuple_list


   # A very short list of all whole-hour UTC offsets, 
# using biggest cities, with and without daylight savings
# NOTE: many timezones have half-hour UTC offsets (and also 15 min);
# these fractional-hour offsets will not work with ODM2.0
tz_key_shortlist = [
    'Pacific/Kiritimati',
    'Pacific/Auckland',
    'Pacific/Tongatapu',
    'Pacific/Fiji',
    'Australia/Sydney',
    'Pacific/Noumea',
    'Asia/Vladivostok',
    'Pacific/Guam',
    'Asia/Tokyo',
    'Pacific/Palau',
    'Asia/Shanghai',
    'Asia/Singapore',
    'Australia/Perth',
    'Asia/Bangkok',
    'Asia/Dhaka',
    'Asia/Karachi',
    'Asia/Dubai',
    'Asia/Istanbul',
    'Europe/Moscow',
    'Africa/Nairobi',
    'Europe/Athens',
    'Asia/Jerusalem',
    'Africa/Douala',
    'Europe/Paris',
    'Africa/Brazzaville',
    'Europe/London',
    'UTC',
    'Atlantic/Cape_Verde',
    'Atlantic/South_Georgia',
    'America/Sao_Paulo',
    'America/Halifax',
    'America/Manaus',
    'US/Eastern',
    'America/Bogota',
    'US/Central',
    'Pacific/Galapagos',
    'US/Mountain',
    'Etc/GMT+7',
    'US/Pacific',
    'Pacific/Pitcairn',
    'US/Alaska',
    'Pacific/Gambier',
    'US/Hawaii',
    'Pacific/Rarotonga',
    'Pacific/Samoa',
    'Pacific/Niue',
    'Etc/GMT+12',
]    