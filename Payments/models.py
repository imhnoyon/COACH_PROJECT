from django.db import models
from Authentication.models import User
from Provider.models import Service


class ServiceBooking(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_bookings")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_bookings")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="bookings")
    booking_date = models.DateField()
    booking_time = models.TimeField()
    session_type = models.CharField(max_length=50, blank=True, null=True)
    session_format = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Booking #{self.id} - {self.user.full_name or self.user.email} for {self.service.title}"


class Payment(models.Model):
    PAYMENT_STATUS = (
        ("created", "Created"),
        ("captured", "Captured"),
        ("completed", "Completed"),
        ("refunded", "Refunded"),
        ("failed", "Failed"),
    )

    order = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name="payments")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer_payments")
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="provider_payments")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)
    provider_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paypal_order_id = models.CharField(max_length=255, unique=True, db_index=True)
    paypal_capture_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="created")
    payment_method = models.CharField(max_length=50, default="paypal")
    captured_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.id} - PayPal Order: {self.paypal_order_id} ({self.payment_status})"


class ProviderWallet(models.Model):
    provider = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet ({self.provider.full_name or self.provider.email}) - Avail: ${self.available_balance}, Pend: ${self.pending_balance}"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    )

    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paypal_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paypal_payout_batch_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payout_item_id = models.CharField(max_length=255, blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="approved_withdrawals")
    approved_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Withdrawal #{self.id} - {self.provider.email} (${self.amount}) [{self.status}]"


class Refund(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="refund")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paypal_refund_id = models.CharField(max_length=255)
    refunded_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    refunded_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Refund #{self.id} for Payment #{self.payment_id} - ${self.refund_amount}"


class PaymentLog(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True, related_name="logs")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Log [{self.event_type}] at {self.created_at}"
