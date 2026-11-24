"""Weekly birthday list for the Sunday announcement and prayer (week = Sunday to Saturday)."""

import calendar
from datetime import date, timedelta
from functools import reduce
from operator import or_

from django.db.models import Q

from .models import Member


def week_bounds(day):
    """Sunday..Saturday week containing `day`."""
    start = day - timedelta(days=(day.weekday() + 1) % 7)
    return start, start + timedelta(days=6)


def _occurrence(birth_date, year):
    # Feb 29 birthdays are celebrated on Feb 28 in common years.
    if birth_date.month == 2 and birth_date.day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return birth_date.replace(year=year)


def birthdays_in_week(day):
    start, end = week_bounds(day)
    days = [start + timedelta(days=i) for i in range(7)]
    conditions = [Q(birth_date__month=d.month, birth_date__day=d.day) for d in days]
    if any(d.month == 2 and d.day == 28 and not calendar.isleap(d.year) for d in days):
        conditions.append(Q(birth_date__month=2, birth_date__day=29))
    members = Member.objects.filter(status__in=Member.ACTIVE_STATUSES).filter(reduce(or_, conditions))
    results = []
    for m in members:
        # The week may span New Year: pick the occurrence that falls inside it.
        for year in {start.year, end.year}:
            when = _occurrence(m.birth_date, year)
            if start <= when <= end:
                results.append({"member": m, "date": when, "turning": when.year - m.birth_date.year})
                break
    results.sort(key=lambda r: (r["date"], r["member"].last_name))
    return start, end, results
