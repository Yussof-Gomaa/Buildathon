from datetime import timedelta
from decimal import Decimal

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

        profile, _ = DriverProfile.objects.get_or_create(
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

        ride, ride_created = Ride.objects.get_or_create(
            driver=sayed,
            route=route,
            status=RideStatus.COMPLETED,
            started_at=timezone.now() - timedelta(hours=3),
            defaults={'ended_at': timezone.now() - timedelta(hours=1)},
        )

        if ride_created:
            sample_passengers = [
                {
                    'pickup_stop': stops[1],
                    'drop_stop': stops[3],
                    'pickup_lat': 30.0135,
                    'pickup_lng': 31.2092,
                    'payment_method': PaymentMethod.CASH,
                },
                {
                    'pickup_stop': stops[2],
                    'drop_stop': stops[5],
                    'pickup_lat': 29.9795,
                    'pickup_lng': 31.1345,
                    'payment_method': PaymentMethod.INSTAPAY,
                },
                {
                    'pickup_stop': stops[1],
                    'drop_stop': stops[4],
                    'pickup_lat': 30.0130,
                    'pickup_lng': 31.2085,
                    'payment_method': PaymentMethod.CASH,
                },
            ]

            for passenger_data in sample_passengers:
                pickup = passenger_data['pickup_stop']
                drop = passenger_data['drop_stop']
                fare = route.compute_fare(pickup, drop)
                payment_method = passenger_data['payment_method']
                Passenger.objects.create(
                    ride=ride,
                    pickup_stop=pickup,
                    drop_stop=drop,
                    pickup_lat=passenger_data['pickup_lat'],
                    pickup_lng=passenger_data['pickup_lng'],
                    fare=fare,
                    payment_method=payment_method,
                    payment_status=(
                        PaymentStatus.PAID
                        if payment_method == PaymentMethod.INSTAPAY
                        else PaymentStatus.PENDING
                    ),
                    ride_status=PassengerRideStatus.DROPPED_OFF,
                )

        self.stdout.write(self.style.SUCCESS('Seed data ready. Review at /admin/'))
