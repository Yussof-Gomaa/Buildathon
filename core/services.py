from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.utils import timezone

from .models import Cost, Passenger, Ride, RideStatus

# Django ExtractWeekDay: Sunday=1 … Saturday=7
WEEKDAY_AR = {
    1: 'الأحد',
    2: 'الاثنين',
    3: 'الثلاثاء',
    4: 'الأربعاء',
    5: 'الخميس',
    6: 'الجمعة',
    7: 'السبت',
}
# Egypt display order: Saturday first
WEEKDAY_ORDER = [7, 1, 2, 3, 4, 5, 6]


def format_hour_label(hour: int) -> str:
    """Arabic hour range label, e.g. 7–8 ص or 5–6 م."""
    end = (hour + 1) % 24

    def part(h: int) -> tuple[int, str]:
        if h == 0:
            return 12, 'ص'
        if h < 12:
            return h, 'ص'
        if h == 12:
            return 12, 'م'
        return h - 12, 'م'

    start_n, start_period = part(hour)
    end_n, end_period = part(end)
    if start_period == end_period:
        return f'{start_n}–{end_n} {start_period}'
    return f'{start_n} {start_period}–{end_n} {end_period}'


def get_active_ride():
    return Ride.objects.filter(status=RideStatus.ACTIVE).select_related('route', 'driver').first()


def overlap_days(range_start: date, range_end: date, window_start: date, window_end: date) -> int:
    start = max(range_start, window_start)
    end = min(range_end, window_end)
    if start > end:
        return 0
    return (end - start).days + 1


def period_bounds(period: str) -> tuple[date, date]:
    today = timezone.localdate()
    if period == 'today':
        return today, today
    if period == 'yesterday':
        day = today - timedelta(days=1)
        return day, day
    if period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == 'month':
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(day=31)
        else:
            end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        return start, end
    if period == 'year':
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    return today, today


def dashboard_stats(driver, start: date, end: date) -> dict:
    income = (
        Passenger.objects.filter(
            ride__driver=driver,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).aggregate(total=Sum('fare'))['total']
        or Decimal('0.00')
    )

    total_cost = Decimal('0.00')
    for cost in Cost.objects.filter(driver=driver):
        cost_start, cost_end = cost.period_window()
        days = overlap_days(start, end, cost_start, cost_end)
        if days:
            total_cost += cost.daily_amortized_amount * Decimal(days)

    return {
        'income': income,
        'cost': total_cost.quantize(Decimal('0.01')),
        'net': (income - total_cost).quantize(Decimal('0.01')),
        'start': start,
        'end': end,
    }


def income_time_insights(driver) -> dict:
    """Recommend best weekday and hour from historical passenger income."""
    cutoff = timezone.now() - timedelta(days=90)
    qs = Passenger.objects.filter(
        ride__driver=driver,
        created_at__gte=cutoff,
    )

    weekday_rows = (
        qs.annotate(weekday=ExtractWeekDay('created_at'))
        .values('weekday')
        .annotate(total=Sum('fare'))
    )
    weekday_totals = {row['weekday']: row['total'] or Decimal('0.00') for row in weekday_rows}

    hour_rows = (
        qs.annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(total=Sum('fare'))
    )
    hour_totals = {row['hour']: row['total'] or Decimal('0.00') for row in hour_rows}

    max_weekday = max((weekday_totals.get(d, Decimal('0.00')) for d in WEEKDAY_ORDER), default=Decimal('0.00'))
    max_hour = max((hour_totals.get(h, Decimal('0.00')) for h in range(24)), default=Decimal('0.00'))

    weekday_heatmap = []
    for day_num in WEEKDAY_ORDER:
        income = weekday_totals.get(day_num, Decimal('0.00'))
        intensity = float(income / max_weekday) if max_weekday else 0.0
        weekday_heatmap.append({
            'day_num': day_num,
            'day': WEEKDAY_AR[day_num],
            'income': income.quantize(Decimal('0.01')),
            'intensity': intensity,
        })

    hour_heatmap = []
    for hour in range(24):
        income = hour_totals.get(hour, Decimal('0.00'))
        intensity = float(income / max_hour) if max_hour else 0.0
        hour_heatmap.append({
            'hour': hour,
            'label': format_hour_label(hour),
            'income': income.quantize(Decimal('0.01')),
            'intensity': intensity,
        })

    has_data = max_weekday > 0

    best_day_name = ''
    best_day_income = Decimal('0.00')
    if has_data:
        best_day = max(WEEKDAY_ORDER, key=lambda d: weekday_totals.get(d, Decimal('0.00')))
        best_day_name = WEEKDAY_AR[best_day]
        best_day_income = weekday_totals.get(best_day, Decimal('0.00')).quantize(Decimal('0.01'))

    best_hour_label = ''
    best_hour_income = Decimal('0.00')
    if max_hour > 0:
        best_hour = max(range(24), key=lambda h: hour_totals.get(h, Decimal('0.00')))
        best_hour_label = format_hour_label(best_hour)
        best_hour_income = hour_totals.get(best_hour, Decimal('0.00')).quantize(Decimal('0.01'))

    return {
        'has_data': has_data,
        'best_day_name': best_day_name,
        'best_day_income': best_day_income,
        'best_hour_label': best_hour_label,
        'best_hour_income': best_hour_income,
        'weekday_heatmap': weekday_heatmap,
        'hour_heatmap': hour_heatmap,
    }


def serialize_passenger(passenger) -> dict:
    return {
        'id': passenger.id,
        'pickup': passenger.pickup_stop.name,
        'drop': passenger.drop_stop.name,
        'fare': str(passenger.fare),
        'payment_method': passenger.payment_method,
        'payment_status': passenger.payment_status,
        'ride_status': passenger.ride_status,
    }


def serialize_stop(stop) -> dict:
    return {
        'id': stop.id,
        'name': stop.name,
        'order': stop.order,
        'cost': str(stop.cost),
    }
