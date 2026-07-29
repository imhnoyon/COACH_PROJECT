from django.contrib import admin
from .models import ServiceBooking


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('id','user','coach','service','booking_date','booking_time','amount','currency','status','payment_status','created_at',)
    list_filter = ('status', 'payment_status', 'booking_date', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'coach__email', 'coach__full_name', 'service__title')
