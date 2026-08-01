from django.contrib import admin
from .models import (
    ServiceBooking,
    ProviderWallet,
    WalletTransaction,
    PaymentTransaction,
    StripeWebhookLog
)


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'coach', 'service', 'product', 'booking_date', 'booking_time', 'amount', 'currency', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'booking_date', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'coach__email', 'coach__full_name', 'service__title', 'product__title')


@admin.register(ProviderWallet)
class ProviderWalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance', 'updated_at')
    search_fields = ('user__email', 'user__full_name')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'transaction_type', 'amount', 'balance_after', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__email', 'description')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'coach', 'gross_amount', 'platform_fee', 'provider_amount', 'status', 'stripe_payment_intent_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer__email', 'coach__email', 'stripe_payment_intent_id')


@admin.register(StripeWebhookLog)
class StripeWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_id', 'event_type', 'processed_at')
    list_filter = ('event_type', 'processed_at')
    search_fields = ('event_id',)

