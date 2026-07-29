from decimal import Decimal
import json
import logging
from django.db import transaction
from django.utils import timezone
from Authentication.models import User
from .models import (
    ServiceBooking,
    Payment,
    ProviderWallet,
    WithdrawalRequest,
    Refund,
    PaymentLog
)
from .paypal_service import PayPalService

logger = logging.getLogger(__name__)


class PaymentService:
    PLATFORM_COMMISSION_RATE = Decimal("0.15")  # 15%

    @classmethod
    @transaction.atomic
    def create_payment_order(cls, booking_id, customer, return_url=None, cancel_url=None):
        """Creates a PayPal order for a service booking."""
        try:
            booking = ServiceBooking.objects.select_for_update().get(id=booking_id)
        except ServiceBooking.DoesNotExist:
            raise ValueError("Service booking not found.")

        if booking.payment_status == "paid":
            raise ValueError("This booking has already been paid for.")

        total_amount = Decimal(str(booking.amount))
        platform_commission = (total_amount * cls.PLATFORM_COMMISSION_RATE).quantize(Decimal("0.01"))
        provider_amount = total_amount - platform_commission

        # Call PayPal API to create Order
        paypal_response = PayPalService.create_order(
            amount=float(total_amount),
            currency=booking.currency,
            return_url=return_url,
            cancel_url=cancel_url
        )

        paypal_order_id = paypal_response.get("id")
        if not paypal_order_id:
            raise ValueError("Failed to retrieve PayPal order ID.")

        payment, created = Payment.objects.update_or_create(
            order=booking,
            defaults={
                "customer": customer,
                "provider": booking.coach,
                "total_amount": total_amount,
                "platform_commission": platform_commission,
                "provider_amount": provider_amount,
                "paypal_order_id": paypal_order_id,
                "payment_status": "created",
                "payment_method": "paypal",
            }
        )

        PaymentLog.objects.create(
            payment=payment,
            event_type="order_created",
            payload={"paypal_response": paypal_response}
        )

        return payment, paypal_response

    @classmethod
    @transaction.atomic
    def capture_payment_order(cls, paypal_order_id, user):
        """Captures a PayPal payment and updates provider wallet pending balance."""
        try:
            payment = Payment.objects.select_for_update().get(paypal_order_id=paypal_order_id)
        except Payment.DoesNotExist:
            raise ValueError("Payment record with given PayPal order ID does not exist.")

        if payment.payment_status in ["captured", "completed"]:
            raise ValueError("Payment has already been captured.")

        # Capture payment via PayPal API
        try:
            paypal_response = PayPalService.capture_order(paypal_order_id)
        except Exception as e:
            err_str = str(e)
            if "ORDER_NOT_APPROVED" in err_str:
                raise ValueError("Payer has not approved the order yet on PayPal. Please approve the payment first using the PayPal approval URL.")
            raise ValueError(f"PayPal capture failed: {err_str}")

        status_str = paypal_response.get("status")
        if status_str != "COMPLETED":
            payment.payment_status = "failed"
            payment.save()
            PaymentLog.objects.create(
                payment=payment,
                event_type="capture_failed",
                payload={"paypal_response": paypal_response}
            )
            raise ValueError(f"PayPal payment capture failed with status: {status_str}")

        # Extract capture ID
        purchase_units = paypal_response.get("purchase_units", [])
        capture_id = None
        if purchase_units:
            payments_data = purchase_units[0].get("payments", {})
            captures = payments_data.get("captures", [])
            if captures:
                capture_id = captures[0].get("id")

        if not capture_id:
            capture_id = f"CAP_{paypal_order_id}"

        # Update Payment record
        payment.paypal_capture_id = capture_id
        payment.payment_status = "captured"
        payment.captured_at = timezone.now()
        payment.save()

        # Update ServiceBooking record
        booking = payment.order
        booking.payment_status = "paid"
        booking.status = "confirmed"
        booking.transaction_id = capture_id
        booking.save()

        # Update Provider Wallet (Delayed Payout: add 85% to pending_balance)
        wallet, _ = ProviderWallet.objects.select_for_update().get_or_create(provider=payment.provider)
        wallet.pending_balance += payment.provider_amount
        wallet.save()

        PaymentLog.objects.create(
            payment=payment,
            event_type="payment_captured",
            payload={"paypal_response": paypal_response}
        )

        return payment

    @classmethod
    @transaction.atomic
    def complete_service(cls, booking_id, user):
        """Marks service as completed and moves provider earnings from pending to available balance."""
        try:
            booking = ServiceBooking.objects.select_for_update().get(id=booking_id)
        except ServiceBooking.DoesNotExist:
            raise ValueError("Booking not found.")

        if booking.coach != user and getattr(user, 'role', None) != 'Admin':
            raise ValueError("Only the service coach or admin can complete this service.")

        if booking.status == "completed":
            raise ValueError("Service has already been completed.")

        payment = Payment.objects.select_for_update().filter(order=booking, payment_status="captured").first()
        if not payment:
            raise ValueError("No captured payment found for this booking.")

        booking.status = "completed"
        booking.save()

        payment.payment_status = "completed"
        payment.save()

        # Move provider amount from pending_balance to available_balance & total_earned
        wallet, _ = ProviderWallet.objects.select_for_update().get_or_create(provider=payment.provider)
        if wallet.pending_balance >= payment.provider_amount:
            wallet.pending_balance -= payment.provider_amount
        else:
            wallet.pending_balance = Decimal("0.00")

        wallet.available_balance += payment.provider_amount
        wallet.total_earned += payment.provider_amount
        wallet.save()

        PaymentLog.objects.create(
            payment=payment,
            event_type="service_completed",
            payload={"booking_id": booking.id, "provider_amount": str(payment.provider_amount)}
        )

        return booking

    @classmethod
    @transaction.atomic
    def process_payment_refund(cls, payment_id, refunded_by, reason=None):
        """Refunds a PayPal payment, cancels booking, and removes pending/available provider balance."""
        try:
            payment = Payment.objects.select_for_update().get(id=payment_id)
        except Payment.DoesNotExist:
            raise ValueError("Payment record not found.")

        if payment.payment_status == "refunded":
            raise ValueError("This payment has already been refunded.")

        if payment.payment_status not in ["captured", "completed"]:
            raise ValueError("Only captured or completed payments can be refunded.")

        if not payment.paypal_capture_id:
            raise ValueError("No PayPal capture ID found for this payment.")

        # Check if provider has already withdrawn these funds
        wallet, _ = ProviderWallet.objects.select_for_update().get_or_create(provider=payment.provider)

        # Execute refund via PayPal API
        paypal_response = PayPalService.refund_capture(
            paypal_capture_id=payment.paypal_capture_id,
            amount=float(payment.total_amount),
            currency=payment.order.currency,
            reason=reason
        )

        paypal_refund_id = paypal_response.get("id") or f"REF_{payment.id}"

        # Create Refund record
        refund = Refund.objects.create(
            payment=payment,
            refund_amount=payment.total_amount,
            paypal_refund_id=paypal_refund_id,
            refunded_by=refunded_by,
            reason=reason or "Customer cancellation / refund request"
        )

        # Reverse provider earnings from wallet
        if payment.payment_status == "captured":
            if wallet.pending_balance >= payment.provider_amount:
                wallet.pending_balance -= payment.provider_amount
            else:
                wallet.pending_balance = Decimal("0.00")
        elif payment.payment_status == "completed":
            if wallet.available_balance >= payment.provider_amount:
                wallet.available_balance -= payment.provider_amount
            else:
                wallet.available_balance = Decimal("0.00")

            if wallet.total_earned >= payment.provider_amount:
                wallet.total_earned -= payment.provider_amount

        wallet.save()

        # Update Payment and ServiceBooking status
        payment.payment_status = "refunded"
        payment.save()

        booking = payment.order
        booking.status = "refunded"
        booking.payment_status = "refunded"
        booking.save()

        PaymentLog.objects.create(
            payment=payment,
            event_type="refund_processed",
            payload={"refund_id": refund.id, "paypal_response": paypal_response}
        )

        return refund

    @classmethod
    @transaction.atomic
    def submit_withdrawal_request(cls, provider, amount, paypal_email):
        """Allows provider to request a payout from available balance."""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        wallet, _ = ProviderWallet.objects.select_for_update().get_or_create(provider=provider)
        if amount > wallet.available_balance:
            raise ValueError(f"Insufficient available balance. Available: ${wallet.available_balance}")

        # Check for any pending request to prevent duplicate submissions
        existing_pending = WithdrawalRequest.objects.filter(provider=provider, status="pending").exists()
        if existing_pending:
            raise ValueError("You already have a pending withdrawal request.")

        request_obj = WithdrawalRequest.objects.create(
            provider=provider,
            amount=amount,
            paypal_email=paypal_email,
            status="pending"
        )

        PaymentLog.objects.create(
            event_type="withdrawal_requested",
            payload={"withdrawal_id": request_obj.id, "provider_id": provider.id, "amount": str(amount)}
        )

        return request_obj

    @classmethod
    @transaction.atomic
    def approve_withdrawal_request(cls, withdrawal_id, admin_user):
        """Admin approves withdrawal request and dispatches funds using PayPal Payouts API."""
        try:
            withdrawal = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_id)
        except WithdrawalRequest.DoesNotExist:
            raise ValueError("Withdrawal request not found.")

        if withdrawal.status in ["approved", "paid"]:
            raise ValueError("This withdrawal request has already been processed.")

        if withdrawal.status == "rejected":
            raise ValueError("Cannot approve a rejected withdrawal request.")

        wallet, _ = ProviderWallet.objects.select_for_update().get_or_create(provider=withdrawal.provider)
        if withdrawal.amount > wallet.available_balance:
            raise ValueError(f"Provider has insufficient available balance (${wallet.available_balance}) for this withdrawal (${withdrawal.amount}).")

        # Execute PayPal Payout
        paypal_response = PayPalService.create_payout(
            receiver_email=withdrawal.paypal_email,
            amount=float(withdrawal.amount),
            currency="USD",
            note=f"Withdrawal Payout #{withdrawal.id}"
        )

        batch_header = paypal_response.get("batch_header", {})
        payout_batch_id = batch_header.get("payout_batch_id")

        payout_item_id = None
        items = paypal_response.get("items", [])
        if items:
            payout_item_id = items[0].get("payout_item_id")

        # Update wallet balance
        wallet.available_balance -= withdrawal.amount
        wallet.total_withdrawn += withdrawal.amount
        wallet.save()

        # Update withdrawal request
        withdrawal.status = "paid"
        withdrawal.paypal_payout_batch_id = payout_batch_id
        withdrawal.paypal_payout_item_id = payout_item_id
        withdrawal.approved_by = admin_user
        withdrawal.approved_at = timezone.now()
        withdrawal.paid_at = timezone.now()
        withdrawal.save()

        PaymentLog.objects.create(
            event_type="withdrawal_approved_and_paid",
            payload={"withdrawal_id": withdrawal.id, "paypal_response": paypal_response}
        )

        return withdrawal

    @classmethod
    @transaction.atomic
    def reject_withdrawal_request(cls, withdrawal_id, admin_user, reason=None):
        """Admin rejects a pending withdrawal request."""
        try:
            withdrawal = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_id)
        except WithdrawalRequest.DoesNotExist:
            raise ValueError("Withdrawal request not found.")

        if withdrawal.status != "pending":
            raise ValueError(f"Cannot reject a withdrawal request with status '{withdrawal.status}'.")

        withdrawal.status = "rejected"
        withdrawal.rejection_reason = reason or "Rejected by admin"
        withdrawal.approved_by = admin_user
        withdrawal.approved_at = timezone.now()
        withdrawal.save()

        PaymentLog.objects.create(
            event_type="withdrawal_rejected",
            payload={"withdrawal_id": withdrawal.id, "reason": reason}
        )

        return withdrawal

    @classmethod
    def handle_webhook_event(cls, headers, raw_body):
        """Handles PayPal webhook events securely."""
        is_valid = PayPalService.verify_webhook_signature(headers, raw_body)
        if not is_valid:
            logger.warning("Invalid PayPal Webhook signature.")
            return False, "Invalid signature"

        body_data = json.loads(raw_body)
        event_type = body_data.get("event_type")
        resource = body_data.get("resource", {})

        PaymentLog.objects.create(
            event_type=f"webhook_{event_type}",
            payload=body_data
        )

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            capture_id = resource.get("id")
            payment = Payment.objects.filter(paypal_capture_id=capture_id).first()
            if payment and payment.payment_status == "created":
                cls.capture_payment_order(payment.paypal_order_id, payment.customer)

        elif event_type in ["PAYMENT.CAPTURE.DENIED", "PAYMENT.CAPTURE.DECLINED"]:
            capture_id = resource.get("id")
            payment = Payment.objects.filter(paypal_capture_id=capture_id).first()
            if payment:
                payment.payment_status = "failed"
                payment.save()

        elif event_type in ["PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"]:
            capture_id = resource.get("id") or resource.get("custom_id")
            payment = Payment.objects.filter(paypal_capture_id=capture_id).first()
            if payment and payment.payment_status != "refunded":
                cls.process_payment_refund(payment.id, None, reason=f"Webhook event {event_type}")

        return True, "Handled"
