"""Deterministic ordinary occurrences for disposable offline compatibility trials."""
from datetime import date, timedelta

from .writer import Appointment


def schedule(start=date(2026, 10, 23), days=14):
    """Two distinct starts per day; no native recurrence or timezone semantics."""
    if type(start) is not date or type(days) is not int or not 1 <= days <= 30:
        raise ValueError('expected start date and 1..30 days')
    events = []
    for n in range(days):
        day = start + timedelta(days=n)
        morning = 570 + 15 * (n % 3)
        afternoon = 855 + 15 * (n % 4)
        events.extend((Appointment(day, morning, morning + 45, f'Plan {n + 1:02d}'),
                       Appointment(day, afternoon, afternoon + 60,
                                   f'{("Review", "Call", "Read")[n % 3]} {n + 1:02d}',
                                   protected_raw=b'q' if n % 5 == 0 else b'1')))
    return tuple(events)
