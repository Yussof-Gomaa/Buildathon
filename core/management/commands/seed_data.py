from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import (
    Cost,
    DriverProfile,
    Passenger,
    PriceType,
    Ride,
    Route,
    RouteStop,
)


class Command(BaseCommand):
    help = 'Seed route, stops, and Sayed user (no sample rides/costs).'

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

        for stop_data in stops_data:
            RouteStop.objects.get_or_create(
                route=route,
                order=stop_data['order'],
                defaults=stop_data,
            )

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

        # Clear transactional data so dashboard shows only real usage
        deleted_passengers, _ = Passenger.objects.filter(ride__driver=sayed).delete()
        deleted_rides, _ = Ride.objects.filter(driver=sayed).delete()
        deleted_costs, _ = Cost.objects.filter(driver=sayed).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Seed ready — route + user only. '
            f'Cleared {deleted_rides} rides, {deleted_passengers} passengers, {deleted_costs} costs.'
        ))
