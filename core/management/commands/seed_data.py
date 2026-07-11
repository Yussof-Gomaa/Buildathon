from datetime import datetime, timedelta
from decimal import Decimal
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Cost,
    CostPeriod,
    DriverProfile,
    Passenger,
    PassengerRideStatus,
    PaymentMethod,
    PaymentStatus,
    PriceType,
    Ride,
    RideStatus,
    Route,
    RouteStop,
)

# Stop pairs for variable fares (pickup_order, drop_order)
STOP_PAIRS = [
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (2, 4),
    (2, 5),
    (2, 6),
    (3, 5),
    (3, 6),
    (4, 6),
]

# Hour slots with base passenger counts (peaks at morning + evening)
HOUR_WEIGHTS = {
    6: 1,
    7: 4,
    8: 5,
    9: 3,
    11: 1,
    13: 2,
    16: 3,
    17: 5,
    18: 4,
    19: 2,
}

# Python weekday: Mon=0 … Sun=6 — boost Tue–Thu
DAY_MULTIPLIER = {
    0: 1.1,  # Mon
    1: 1.35,  # Tue
    2: 1.4,  # Wed — strongest
    3: 1.3,  # Thu
    4: 0.35,  # Fri — light
    5: 0.9,  # Sat
    6: 0.85,  # Sun
}

HISTORY_DAYS = 28
MIN_COMPLETED_RIDES_FOR_SKIP = 20


class Command(BaseCommand):
    help = 'Seed demo data for Sayed microbus app (idempotent).'

    def handle(self, *args, **options):
        route, _ = Route.objects.get_or_create(
            name='الطريق الرئيسي – الجيزة',
            defaults={
                'price_type': PriceType.VARIABLE,
                'is_active': True,
            },
        )

        stops_data = [
            {'name': 'ميدان الجيزة', 'order': 1, 'cost': Decimal('0.00'), 'lat': 30.0131, 'lng': 31.2089},
            {'name': 'شارع الهرم', 'order': 2, 'cost': Decimal('3.00'), 'lat': 29.9792, 'lng': 31.1342},
            {'name': 'فيصل', 'order': 3, 'cost': Decimal('4.00'), 'lat': 29.9600, 'lng': 31.1200},
            {'name': 'الدقي', 'order': 4, 'cost': Decimal('5.00'), 'lat': 30.0370, 'lng': 31.2100},
            {'name': 'المهندسين', 'order': 5, 'cost': Decimal('4.00'), 'lat': 30.0500, 'lng': 31.2000},
            {'name': 'أبو النمرس', 'order': 6, 'cost': Decimal('6.00'), 'lat': 29.8900, 'lng': 31.2500},
        ]

        stops = {}
        for stop_data in stops_data:
            stop, _ = RouteStop.objects.get_or_create(
                route=route,
                order=stop_data['order'],
                defaults=stop_data,
            )
            stops[stop_data['order']] = stop

        sayed, created = User.objects.get_or_create(
            username='sayed',
            defaults={
                'first_name': 'سيد',
                'last_name': 'السائق',
                'is_staff': True,
            },
        )
        if created:
            sayed.set_password('sayed123')
            sayed.save()
            self.stdout.write(self.style.SUCCESS('Created user sayed / sayed123'))
        else:
            self.stdout.write('User sayed already exists')

        DriverProfile.objects.get_or_create(
            user=sayed,
            defaults={
                'route': route,
                'max_capacity': 14,
                'instapay_handle': 'sayed.microbus@instapay',
            },
        )

        Cost.objects.get_or_create(
            driver=sayed,
            note='ديزل',
            date_incurred=timezone.localdate(),
            defaults={
                'amount': Decimal('350.00'),
                'period': CostPeriod.DAY,
            },
        )
        Cost.objects.get_or_create(
            driver=sayed,
            note='دفعة للمالك',
            date_incurred=timezone.localdate().replace(day=1),
            defaults={
                'amount': Decimal('3000.00'),
                'period': CostPeriod.MONTH,
            },
        )

        completed = Ride.objects.filter(driver=sayed, status=RideStatus.COMPLETED).count()
        if completed >= MIN_COMPLETED_RIDES_FOR_SKIP:
            self.stdout.write(
                f'History already seeded ({completed} completed rides) — skipping ride history'
            )
            self.stdout.write(self.style.SUCCESS('Seed data ready. Review at /admin/'))
            return

        # Remove thin sample rides so we can rebuild a full history once
        Ride.objects.filter(driver=sayed, status=RideStatus.COMPLETED).delete()

        rng = random.Random(42)
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        rides_created = 0
        passengers_created = 0

        for day_offset in range(HISTORY_DAYS, 0, -1):
            day = today - timedelta(days=day_offset)
            day_mult = DAY_MULTIPLIER[day.weekday()]

            for hour, base_count in HOUR_WEIGHTS.items():
                count = max(1, int(round(base_count * day_mult)))
                if day_mult < 0.5 and hour not in (8, 17):
                    # Friday: only keep peak slots
                    continue

                started = timezone.make_aware(
                    datetime(day.year, day.month, day.day, hour, rng.randint(0, 20)),
                    tz,
                )
                ended = started + timedelta(minutes=rng.randint(35, 55))

                ride = Ride(
                    driver=sayed,
                    route=route,
                    status=RideStatus.COMPLETED,
                )
                ride.save()
                Ride.objects.filter(pk=ride.pk).update(
                    started_at=started,
                    ended_at=ended,
                )
                rides_created += 1

                for i in range(count):
                    pickup_order, drop_order = rng.choice(STOP_PAIRS)
                    pickup = stops[pickup_order]
                    drop = stops[drop_order]
                    fare = route.compute_fare(pickup, drop)
                    payment_method = (
                        PaymentMethod.INSTAPAY if rng.random() < 0.35 else PaymentMethod.CASH
                    )
                    created_at = started + timedelta(minutes=2 + i * 3 + rng.randint(0, 2))

                    passenger = Passenger(
                        ride=ride,
                        pickup_stop=pickup,
                        drop_stop=drop,
                        pickup_lat=pickup.lat + rng.uniform(-0.001, 0.001),
                        pickup_lng=pickup.lng + rng.uniform(-0.001, 0.001),
                        fare=fare,
                        payment_method=payment_method,
                        payment_status=(
                            PaymentStatus.PAID
                            if payment_method == PaymentMethod.INSTAPAY
                            else PaymentStatus.PAID
                        ),
                        ride_status=PassengerRideStatus.DROPPED_OFF,
                    )
                    passenger.save()
                    Passenger.objects.filter(pk=passenger.pk).update(created_at=created_at)
                    passengers_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {rides_created} rides and {passengers_created} passengers over {HISTORY_DAYS} days'
            )
        )
        self.stdout.write(self.style.SUCCESS('Seed data ready. Review at /admin/'))
