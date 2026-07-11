from django.contrib import admin

from .models import Cost, DriverProfile, Passenger, Ride, Route, RouteStop


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    ordering = ['order']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_type', 'fixed_price', 'is_active']
    list_filter = ['price_type', 'is_active']
    search_fields = ['name']
    inlines = [RouteStopInline]


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ['name', 'route', 'order', 'cost', 'lat', 'lng']
    list_filter = ['route']
    search_fields = ['name', 'route__name']
    ordering = ['route', 'order']


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'route', 'max_capacity', 'instapay_handle']
    list_filter = ['route']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'instapay_handle']


class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0
    readonly_fields = ['created_at']
    fields = [
        'pickup_stop',
        'drop_stop',
        'fare',
        'payment_method',
        'payment_status',
        'ride_status',
        'created_at',
    ]


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'route', 'status', 'started_at', 'ended_at', 'active_passenger_count']
    list_filter = ['status', 'route']
    search_fields = ['driver__username']
    inlines = [PassengerInline]


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'ride',
        'pickup_stop',
        'drop_stop',
        'fare',
        'payment_method',
        'payment_status',
        'ride_status',
        'created_at',
    ]
    list_filter = ['payment_method', 'payment_status', 'ride_status']
    search_fields = ['pickup_stop__name', 'drop_stop__name']


@admin.register(Cost)
class CostAdmin(admin.ModelAdmin):
    list_display = ['driver', 'amount', 'period', 'date_incurred', 'note', 'daily_amortized_amount']
    list_filter = ['period', 'date_incurred']
    search_fields = ['note', 'driver__username']
