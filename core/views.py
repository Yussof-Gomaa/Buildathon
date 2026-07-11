import io
import json

import qrcode
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Cost,
    CostPeriod,
    DriverProfile,
    Passenger,
    PassengerRideStatus,
    PaymentMethod,
    PaymentStatus,
    Ride,
    RideStatus,
    RouteStop,
)
from .services import (
    dashboard_stats,
    get_active_ride,
    period_bounds,
    serialize_passenger,
    serialize_stop,
)


def passenger_home(request):
    return render(request, 'core/passenger_home.html')


@require_GET
def api_active_ride(request):
    ride = get_active_ride()
    if not ride:
        return JsonResponse({'active': False})

    profile = DriverProfile.objects.filter(user=ride.driver).first()
    all_stops = [serialize_stop(s) for s in ride.route.stops.all()]

    pickup_stop_id = request.GET.get('pickup_stop_id')
    if not pickup_stop_id:
        return JsonResponse({
            'active': True,
            'ride_id': ride.id,
            'route_name': ride.route.name,
            'instapay_handle': profile.instapay_handle if profile else '',
            'all_stops': all_stops,
            'needs_pickup': True,
            'capacity': profile.max_capacity if profile else 14,
            'active_count': ride.active_passenger_count,
        })

    pickup_stop = get_object_or_404(RouteStop, pk=pickup_stop_id, route=ride.route)
    drop_stops = ride.route.stops.filter(order__gt=pickup_stop.order)

    return JsonResponse({
        'active': True,
        'ride_id': ride.id,
        'route_name': ride.route.name,
        'instapay_handle': profile.instapay_handle if profile else '',
        'pickup_stop': serialize_stop(pickup_stop),
        'drop_stops': [serialize_stop(s) for s in drop_stops],
        'all_stops': all_stops,
        'capacity': profile.max_capacity if profile else 14,
        'active_count': ride.active_passenger_count,
    })


@require_POST
def api_fare_preview(request):
    try:
        data = json.loads(request.body)
        ride = get_object_or_404(Ride, pk=data['ride_id'], status=RideStatus.ACTIVE)
        drop_stop = get_object_or_404(RouteStop, pk=data['drop_stop_id'], route=ride.route)
        pickup_stop = get_object_or_404(
            RouteStop, pk=data['pickup_stop_id'], route=ride.route
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'بيانات غير صالحة.'}, status=400)

    try:
        fare = ride.route.compute_fare(pickup_stop, drop_stop)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    return JsonResponse({
        'fare': str(fare),
        'pickup_stop_name': pickup_stop.name,
        'drop_stop_name': drop_stop.name,
        'pickup_stop_id': pickup_stop.id,
    })


@require_POST
def api_checkout(request):
    try:
        data = json.loads(request.body)
        ride = get_object_or_404(Ride, pk=data['ride_id'], status=RideStatus.ACTIVE)
        drop_stop = get_object_or_404(RouteStop, pk=data['drop_stop_id'], route=ride.route)
        pickup_stop = get_object_or_404(
            RouteStop, pk=data['pickup_stop_id'], route=ride.route
        )
        payment_method = data['payment_method']
        if payment_method not in PaymentMethod.values:
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'بيانات غير صالحة.'}, status=400)

    profile = DriverProfile.objects.filter(user=ride.driver).first()
    max_capacity = profile.max_capacity if profile else 14
    if ride.active_passenger_count >= max_capacity:
        return JsonResponse({'error': 'السيارة ممتلئة.'}, status=400)

    try:
        fare = ride.route.compute_fare(pickup_stop, drop_stop)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    passenger = Passenger.objects.create(
        ride=ride,
        pickup_stop=pickup_stop,
        drop_stop=drop_stop,
        pickup_lat=pickup_stop.lat,
        pickup_lng=pickup_stop.lng,
        fare=fare,
        payment_method=payment_method,
    )

    return JsonResponse({'ok': True, 'fare': str(passenger.fare), 'passenger_id': passenger.id})


@require_GET
def qr_code(request):
    text = request.GET.get('text', '')
    if not text:
        return HttpResponse(status=400)

    img = qrcode.make(text)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')


class DriverLoginView(LoginView):
    template_name = 'core/driver_login.html'
    redirect_authenticated_user = True


def driver_logout_view(request):
    logout(request)
    return redirect('driver_login')


@login_required
def driver_home(request):
    return render(request, 'core/driver_home.html')


@login_required
@require_GET
def driver_api_state(request):
    profile = get_object_or_404(DriverProfile, user=request.user)
    ride = Ride.objects.filter(driver=request.user, status=RideStatus.ACTIVE).first()
    stops = [serialize_stop(s) for s in profile.route.stops.all()]

    if not ride:
        return JsonResponse({
            'active_ride': False,
            'route_name': profile.route.name,
            'max_capacity': profile.max_capacity,
            'stops': stops,
        })

    passengers = ride.passengers.filter(ride_status=PassengerRideStatus.IN_CAR).select_related(
        'pickup_stop', 'drop_stop'
    )
    next_stop = ride.get_next_stop()
    dropping = list(ride.passengers_dropping_at(next_stop)) if next_stop else []

    payload = {
        'active_ride': True,
        'ride_id': ride.id,
        'route_name': profile.route.name,
        'max_capacity': profile.max_capacity,
        'active_count': ride.active_passenger_count,
        'passengers': [serialize_passenger(p) for p in passengers],
        'stops': stops,
        'current_stop': serialize_stop(ride.current_stop) if ride.current_stop else None,
    }
    if next_stop:
        payload['next_stop'] = serialize_stop(next_stop)
        payload['dropping_count'] = len(dropping)
        payload['dropping_at_next'] = [serialize_passenger(p) for p in dropping]
    else:
        payload['next_stop'] = None
        payload['dropping_count'] = 0
        payload['route_finished'] = ride.current_stop_id is not None

    return JsonResponse(payload)


@login_required
@require_POST
def driver_ride_start(request):
    profile = get_object_or_404(DriverProfile, user=request.user)
    if Ride.objects.filter(driver=request.user, status=RideStatus.ACTIVE).exists():
        return JsonResponse({'error': 'يوجد رحلة نشطة بالفعل.'}, status=400)

    ride = Ride.objects.create(driver=request.user, route=profile.route)
    return JsonResponse({'ok': True, 'ride_id': ride.id})


@login_required
@require_POST
def driver_ride_arrive(request):
    ride = Ride.objects.filter(
        driver=request.user,
        status=RideStatus.ACTIVE,
    ).select_related('route', 'current_stop').first()
    if not ride:
        return JsonResponse({'error': 'مفيش رحلة شغالة.'}, status=400)

    next_stop = ride.get_next_stop()
    if not next_stop:
        return JsonResponse({'error': 'خلصنا كل المحطات.'}, status=400)

    dropping = ride.passengers_dropping_at(next_stop)
    dropped_count = dropping.count()
    dropping.update(ride_status=PassengerRideStatus.DROPPED_OFF)

    ride.current_stop = next_stop
    ride.save(update_fields=['current_stop'])

    following = ride.get_next_stop()
    return JsonResponse({
        'ok': True,
        'arrived_at': next_stop.name,
        'dropped_count': dropped_count,
        'next_stop': serialize_stop(following) if following else None,
    })


@login_required
@require_POST
def driver_ride_end(request):
    ride = Ride.objects.filter(driver=request.user, status=RideStatus.ACTIVE).first()
    if not ride:
        return JsonResponse({'error': 'لا توجد رحلة نشطة.'}, status=400)

    ride.status = RideStatus.COMPLETED
    ride.ended_at = timezone.now()
    ride.save(update_fields=['status', 'ended_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def driver_passenger_add(request):
    profile = get_object_or_404(DriverProfile, user=request.user)
    ride = Ride.objects.filter(driver=request.user, status=RideStatus.ACTIVE).first()
    if not ride:
        return JsonResponse({'error': 'ابدأ الرحلة أولاً.'}, status=400)

    try:
        data = json.loads(request.body)
        pickup_stop = get_object_or_404(RouteStop, pk=data['pickup_stop_id'], route=profile.route)
        drop_stop = get_object_or_404(RouteStop, pk=data['drop_stop_id'], route=profile.route)
        payment_method = data.get('payment_method', PaymentMethod.CASH)
    except (KeyError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'بيانات غير صالحة.'}, status=400)

    if ride.active_passenger_count >= profile.max_capacity:
        return JsonResponse({'error': 'السيارة ممتلئة.'}, status=400)

    try:
        fare = profile.route.compute_fare(pickup_stop, drop_stop)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    passenger = Passenger.objects.create(
        ride=ride,
        pickup_stop=pickup_stop,
        drop_stop=drop_stop,
        pickup_lat=pickup_stop.lat,
        pickup_lng=pickup_stop.lng,
        fare=fare,
        payment_method=payment_method,
    )
    return JsonResponse({'ok': True, 'passenger': serialize_passenger(passenger)})


@login_required
@require_POST
def driver_verify_cash(request, passenger_id):
    passenger = get_object_or_404(
        Passenger,
        pk=passenger_id,
        ride__driver=request.user,
        payment_method=PaymentMethod.CASH,
    )
    passenger.payment_status = PaymentStatus.PAID
    passenger.save(update_fields=['payment_status'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def driver_passenger_drop(request, passenger_id):
    passenger = get_object_or_404(Passenger, pk=passenger_id, ride__driver=request.user)
    passenger.ride_status = PassengerRideStatus.DROPPED_OFF
    passenger.save(update_fields=['ride_status'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def driver_passenger_cancel(request, passenger_id):
    passenger = get_object_or_404(Passenger, pk=passenger_id, ride__driver=request.user)
    passenger.ride_status = PassengerRideStatus.CANCELLED
    passenger.save(update_fields=['ride_status'])
    return JsonResponse({'ok': True})


@login_required
def driver_expense(request):
    if request.method == 'POST':
        try:
            amount = request.POST['amount']
            period = request.POST.get('period', CostPeriod.ONE_OFF)
            note = request.POST.get('note', '')
            Cost.objects.create(
                driver=request.user,
                amount=amount,
                period=period,
                note=note,
            )
            return redirect('driver_expense')
        except (KeyError, ValueError):
            pass

    recent_costs = Cost.objects.filter(driver=request.user)[:10]
    period_choices = [
        (CostPeriod.ONE_OFF, 'مرة واحدة'),
        (CostPeriod.DAY, 'كل يوم'),
        (CostPeriod.WEEK, 'كل أسبوع'),
        (CostPeriod.MONTH, 'كل شهر'),
        (CostPeriod.YEAR, 'كل سنة'),
    ]
    return render(request, 'core/driver_expense.html', {
        'recent_costs': recent_costs,
        'period_choices': period_choices,
    })


@login_required
def driver_dashboard(request):
    period = request.GET.get('period', 'today')
    start, end = period_bounds(period)
    stats = dashboard_stats(request.user, start, end)
    periods = [
        ('today', 'النهاردة'),
        ('yesterday', 'امبارح'),
        ('week', 'الأسبوع'),
        ('month', 'الشهر'),
        ('year', 'السنة'),
    ]
    return render(request, 'core/driver_dashboard.html', {
        'period': period,
        'periods': periods,
        'stats': stats,
    })
