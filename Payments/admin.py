from django.contrib import admin
from .models import (
    ServiceBooking,
    Payment,
    ProviderWallet,
    WithdrawalRequest,
    Refund,
    PaymentLog
)


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'coach',
        'service',
        'booking_date',
        'booking_time',
        'amount',
        'currency',
        'status',
        'payment_status',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'booking_date', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'coach__email', 'coach__full_name', 'service__title')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'customer',
        'provider',
        'total_amount',
        'platform_commission',
        'provider_amount',
        'paypal_order_id',
        'paypal_capture_id',
        'payment_status',
        'captured_at',
    )
    list_filter = ('payment_status', 'payment_method', 'created_at')
    search_fields = ('paypal_order_id', 'paypal_capture_id', 'customer__email', 'provider__email')


@admin.register(ProviderWallet)
class ProviderWalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'provider',
        'available_balance',
        'pending_balance',
        'total_earned',
        'total_withdrawn',
        'updated_at',
    )
    search_fields = ('provider__email', 'provider__full_name')


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'provider',
        'amount',
        'paypal_email',
        'status',
        'paypal_payout_batch_id',
        'approved_by',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('provider__email', 'paypal_email', 'paypal_payout_batch_id')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'payment',
        'refund_amount',
        'paypal_refund_id',
        'refunded_by',
        'refunded_at',
    )
    search_fields = ('paypal_refund_id', 'payment__paypal_order_id')


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'event_type', 'created_at')
    list_filter = ('event_type', 'created_at')
