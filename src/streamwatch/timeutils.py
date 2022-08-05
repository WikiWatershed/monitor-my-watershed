from datetime import datetime
from math import trunc
from typing import Tuple, List
import zoneinfo

# Calculate local current UTC Offset
def get_utcoffset(tz_key: str = None) -> Tuple[int, str, str]:
    '''
    Calculate standard time UTC offset integer and short name 
    for a given IANA timezone key.
    
    tz_key: if None it is based on timezone information
    from the operating system.
    
    WARNING: Conversion from daylight savings to standard time
    will not likely work in the southern hemisphere. 
    '''

    dt_winter = datetime(2022, 1, 1)
    if not tz_key:
        # Get local timzone
        dt_now = dt_winter.astimezone() 
    else:
        # Get local timzone
        dt_now = dt_winter.astimezone(zoneinfo.ZoneInfo(tz_key)) 
    
    utc_offset = dt_now.utcoffset().total_seconds() / (60*60)
    utc_offset_int = trunc(utc_offset)
    
    return utc_offset_int, dt_now.isoformat()[-6:], dt_now.tzname()


def make_tz_tuple_list() -> List:
    '''
    Creates a list of tuples with:
    - `zoneinfo` timezone keys
    - display field for timezone info
    '''
    tz_tuple_list = []
    for tz_key in zoneinfo.available_timezones():
        tz_info = get_utcoffset(tz_key)
        tz_display = f"UTC{tz_info[1]} {tz_key} ({tz_info[2]})"
        tz_tuple = (tz_key, tz_display)
        tz_tuple_list.append(tz_tuple)
    
    def item2(tz_tuple):
        return get_utcoffset(tz_tuple[0])[0]
    
    tz_tuple_list.sort(reverse=True, key=item2)
    return tz_tuple_list
    
    