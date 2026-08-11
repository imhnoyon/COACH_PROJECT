from django.db import models
from Authentication.models import User
from Provider.models import Service, Product


class ServiceBooking(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_bookings")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_bookings")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="bookings", null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bookings", null=True, blank=True)
    booking_date = models.DateField(null=True, blank=True)
    booking_time = models.TimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    refund_status = models.CharField(max_length=20, blank=True, null=True)
    refund_id = models.CharField(max_length=255, blank=True, null=True)
    refunded_at = models.DateTimeField(blank=True, null=True)
    is_rescheduled = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        item_title = self.service.title if self.service else (self.product.title if self.product else "N/A")
        return f"Order #{self.id} - {self.user.full_name or self.user.email} for {item_title}"


class ProviderWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.user.email} - Balance: {self.balance}"


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(ProviderWallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, default='credit')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    booking = models.ForeignKey(ServiceBooking, on_delete=models.SET_NULL, null=True, blank=True, related_name="wallet_transactions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Credit {self.amount} to {self.wallet.user.email}"


class PaymentTransaction(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_payments")
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name="payment_transactions", null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_application_fee_id = models.CharField(max_length=255, blank=True, null=True)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2)
    provider_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, default='succeeded')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tx {self.stripe_payment_intent_id} - Gross: {self.gross_amount}"


class StripeWebhookLog(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"

