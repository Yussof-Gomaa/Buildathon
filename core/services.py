from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Cost, Passenger, Ride, RideStatus


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


def serialize_passenger(passenger) -> dict:
    return {
        'id': passenger.id,
        'pickup': passenger.pickup_stop.name,
        'drop': passenger.drop_stop.name,
        'drop_stop_id': passenger.drop_stop_id,
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
        'lat': stop.lat,
        'lng': stop.lng,
    }
