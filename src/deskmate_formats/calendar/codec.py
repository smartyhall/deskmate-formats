"""SDK-derived ordinary-event codecs; native boundary/sentinel cases excluded.

See docs/research/sdk-calendar-database.md. Representable years are not a claim
about the application's date-entry limits. No timezone or recurrence is encoded.
"""
from datetime import date


def encode_date(day):
    if type(day) is not date or not 1980 <= day.year <= 2138:
        raise ValueError('SDK date requires a calendar-valid date in representable years 1980..2138')
    return bytes((day.year - 1980 + 0x61, day.month + 0x61, day.day + 0x61))


def decode_date(raw):
    if len(raw) != 3 or raw[0] < 0x61:
        raise ValueError('invalid ordinary SDK date')
    return date(1980 + raw[0] - 0x61, raw[1] - 0x61, raw[2] - 0x61)


def encode_time(minutes):
    # 80/E0/F0 have context-sensitive sentinel meanings; deliberately excluded.
    if type(minutes) is not int or not 15 <= minutes <= 1425 or minutes % 15:
        raise ValueError('ordinary SDK time requires quarter hours 00:15..23:45')
    return bytes((0x80 | ((minutes // 60) << 2) | ((minutes % 60) // 15),))


def decode_time(raw):
    if len(raw) != 1 or not 0x81 <= raw[0] <= 0xDF:
        raise ValueError('unsupported blank/midnight/sentinel time')
    return ((raw[0] >> 2) & 31) * 60 + (raw[0] & 3) * 15
