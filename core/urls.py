from django.urls import path

from . import views

urlpatterns = [
    path('', views.passenger_home, name='passenger_home'),
    path('api/ride/active/', views.api_active_ride, name='api_active_ride'),
    path('api/fare/preview/', views.api_fare_preview, name='api_fare_preview'),
    path('api/passenger/checkout/', views.api_checkout, name='api_checkout'),
    path('qr/', views.qr_code, name='qr_code'),

    path('driver/login/', views.DriverLoginView.as_view(), name='driver_login'),
    path('driver/logout/', views.driver_logout_view, name='driver_logout'),
    path('driver/', views.driver_home, name='driver_home'),
    path('driver/api/state/', views.driver_api_state, name='driver_api_state'),
    path('driver/api/ride/start/', views.driver_ride_start, name='driver_ride_start'),
    path('driver/api/ride/end/', views.driver_ride_end, name='driver_ride_end'),
    path('driver/api/passenger/add/', views.driver_passenger_add, name='driver_passenger_add'),
    path('driver/api/passenger/<int:passenger_id>/verify-cash/', views.driver_verify_cash, name='driver_verify_cash'),
    path('driver/api/passenger/<int:passenger_id>/drop/', views.driver_passenger_drop, name='driver_passenger_drop'),
    path('driver/api/passenger/<int:passenger_id>/cancel/', views.driver_passenger_cancel, name='driver_passenger_cancel'),
    path('driver/expense/', views.driver_expense, name='driver_expense'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/analysis/', views.driver_analysis, name='driver_analysis'),
]
