import math
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PriceType(models.TextChoices):
    FIXED = 'FIXED', 'ثابت'
    VARIABLE = 'VARIABLE', 'متغير'


class RideStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'نشط'
    COMPLETED = 'COMPLETED', 'منتهي'


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'نقدي'
    INSTAPAY = 'INSTAPAY', 'إنستاباي'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'قيد الانتظار'
    PAID = 'PAID', 'مدفوع'


class PassengerRideStatus(models.TextChoices):
    IN_CAR = 'IN_CAR', 'في السيارة'
    DROPPED_OFF = 'DROPPED_OFF', 'نزل'
    CANCELLED = 'CANCELLED', 'ملغي'


class CostPeriod(models.TextChoices):
    ONE_OFF = 'ONE_OFF', 'مرة واحدة'
    DAY = 'DAY', 'يوم'
    WEEK = 'WEEK', 'أسبوع'
    MONTH = 'MONTH', 'شهر'
    YEAR = 'YEAR', 'سنة'


def haversine_km(lat1, lng1, lat2, lng2):
    """Return great-circle distance in kilometers between two coordinates."""
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Route(models.Model):
    name = models.CharField(max_length=200)
    price_type = models.CharField(
        max_length=10,
        choices=PriceType.choices,
        default=PriceType.VARIABLE,
    )
    fixed_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        if self.price_type == PriceType.FIXED and self.fixed_price is None:
            raise ValidationError({'fixed_price': 'السعر الثابت مطلوب للمسار الثابت.'})
        if self.price_type == PriceType.VARIABLE and self.fixed_price is not None:
            raise ValidationError({'fixed_price': 'لا يُستخدم السعر الثابت مع المسار المتغير.'})

    def nearest_stop(self, lat, lng):
        stops = list(self.stops.all())
        if not stops:
            return None
        return min(stops, key=lambda stop: haversine_km(lat, lng, stop.lat, stop.lng))

    def compute_fare(self, pickup_stop, drop_stop):
        if pickup_stop.route_id != self.pk or drop_stop.route_id != self.pk:
            raise ValidationError('نقاط الالتقاط والنزول يجب أن تكون على نفس المسار.')
        if pickup_stop.order >= drop_stop.order:
            raise ValidationError('نقطة النزول يجب أن تكون بعد نقطة الالتقاط.')

        if self.price_type == PriceType.FIXED:
            return self.fixed_price

        total = self.stops.filter(
            order__gt=pickup_stop.order,
            order__lte=drop_stop.order,
        ).aggregate(total=models.Sum('cost'))['total']
        return total or Decimal('0.00')


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        ordering = ['route', 'order']
        unique_together = [['route', 'order']]

    def __str__(self):
        return f'{self.route.name} — {self.name}'


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name='drivers')
    max_capacity = models.PositiveIntegerField(default=14)
    instapay_handle = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Ride(models.Model):
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides')
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name='rides')
    status = models.CharField(
        max_length=10,
        choices=RideStatus.choices,
        default=RideStatus.ACTIVE,
    )
    current_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='rides_here',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'رحلة {self.pk} — {self.driver.username}'

    @property
    def active_passenger_count(self):
        return self.passengers.filter(ride_status=PassengerRideStatus.IN_CAR).count()

    def get_next_stop(self):
        stops = self.route.stops.order_by('order')
        if self.current_stop_id is None:
            return stops.first()
        return stops.filter(order__gt=self.current_stop.order).first()

    def passengers_dropping_at(self, stop):
        return self.passengers.filter(
            drop_stop=stop,
            ride_status=PassengerRideStatus.IN_CAR,
        )


class Passenger(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='passengers')
    pickup_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.PROTECT,
        related_name='pickup_passengers',
    )
    drop_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.PROTECT,
        related_name='drop_passengers',
    )
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    ride_status = models.CharField(
        max_length=12,
        choices=PassengerRideStatus.choices,
        default=PassengerRideStatus.IN_CAR,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'راكب {self.pk} — {self.pickup_stop.name} → {self.drop_stop.name}'

    def save(self, *args, **kwargs):
        if self.payment_method == PaymentMethod.INSTAPAY:
            self.payment_status = PaymentStatus.PAID
        elif self.payment_method == PaymentMethod.CASH and not self.pk:
            self.payment_status = PaymentStatus.PENDING
        super().save(*args, **kwargs)


class Cost(models.Model):
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='costs')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(max_length=10, choices=CostPeriod.choices, default=CostPeriod.ONE_OFF)
    date_incurred = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-date_incurred', '-pk']

    def __str__(self):
        return f'{self.amount} — {self.get_period_display()}'

    def period_window(self):
        date = self.date_incurred
        if self.period == CostPeriod.ONE_OFF:
            return date, date
        if self.period == CostPeriod.DAY:
            return date, date
        if self.period == CostPeriod.WEEK:
            start = date - timedelta(days=date.weekday())
            return start, start + timedelta(days=6)
        if self.period == CostPeriod.MONTH:
            start = date.replace(day=1)
            if date.month == 12:
                end = date.replace(day=31)
            else:
                end = (date.replace(month=date.month + 1, day=1) - timedelta(days=1))
            return start, end
        if self.period == CostPeriod.YEAR:
            start = date.replace(month=1, day=1)
            end = date.replace(month=12, day=31)
            return start, end
        return date, date

    @property
    def daily_amortized_amount(self):
        start, end = self.period_window()
        days = (end - start).days + 1
        return self.amount / Decimal(days)
