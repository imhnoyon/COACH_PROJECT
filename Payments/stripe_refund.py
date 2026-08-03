import logging
import os
import stripe
from django.conf import settings
from django.utils import timezone
from Payments.models import ServiceBooking, PaymentTransaction, ProviderWallet, WalletTransaction

# Set Stripe API key
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.environ.get('STRIPE_SECRET_KEY')

logger = logging.getLogger(__name__)


class StripeRefundService:
    @classmethod
    def refund_booking(cls, booking: ServiceBooking):
        """
        Handles Stripe refund for a ServiceBooking.
        If a connected Stripe transfer exists, it reverses the transfer from the coach and
        refunds the platform application fee.
        Also updates the database states and debits the coach's local wallet balance.
        """
        logger.info(f"Refund process started for booking ID: {booking.id}")

        # Find the payment transaction
        payment_tx = PaymentTransaction.objects.filter(booking=booking).first()
        if not payment_tx:
            logger.error(f"Refund failed: PaymentTransaction not found for booking ID {booking.id}")
            raise ValueError("Payment transaction not found for this booking.")

        pi_id = payment_tx.stripe_payment_intent_id
        if not pi_id:
            logger.error(f"Refund failed: stripe_payment_intent_id is missing for booking ID {booking.id}")
            raise ValueError("Stripe Payment Intent ID is missing for this transaction.")

        # 1. Retrieve the PaymentIntent to gather IDs (Charge, Transfer, Application Fee) if not stored
        logger.info(f"Retrieving Payment Intent {pi_id} from Stripe")
        payment_intent = stripe.PaymentIntent.retrieve(pi_id)
        
        charge_id = getattr(payment_intent, 'latest_charge', None)  
        transfer_id = None
        application_fee_id = None
        
        if charge_id:
            logger.info(f"Retrieving Charge {charge_id} from Stripe")
            charge = stripe.Charge.retrieve(charge_id)
            transfer_id = getattr(charge, 'transfer', None)
            application_fee_id = getattr(charge, 'application_fee', None)

        # Update PaymentTransaction with resolved Stripe IDs
        payment_tx.stripe_charge_id = charge_id
        payment_tx.stripe_transfer_id = transfer_id
        payment_tx.stripe_application_fee_id = application_fee_id
        payment_tx.save()
        if transfer_id:
            logger.info(f"Reversing transfer {transfer_id} and refunding application fee {application_fee_id}")
            refund = stripe.Refund.create(
                payment_intent=pi_id,
                reverse_transfer=True,
                refund_application_fee=True
            )
        else:
            logger.info(f"Performing standard refund on PaymentIntent {pi_id}")
            refund = stripe.Refund.create(
                payment_intent=pi_id
            )
        refund_id = refund.id
        logger.info(f"Stripe Refund succeeded. Refund ID: {refund_id}")
        # 3. Update database records
        booking.payment_status = "refunded"
        booking.refund_status = "completed"
        booking.refund_id = refund_id
        booking.refunded_at = timezone.now()
        booking.status = "rejected"
        booking.save()
        payment_tx.status = "refunded"
        payment_tx.save()
        # 4. Deduct the provider earnings from the coach's local wallet
        wallet, _ = ProviderWallet.objects.get_or_create(user=booking.coach)
        wallet.balance = wallet.balance - payment_tx.provider_amount
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            amount=payment_tx.provider_amount,
            balance_after=wallet.balance,
            description=f"Refund debit for rejected booking #{booking.id}",
            booking=booking
        )
        
        logger.info(f"Deducted {payment_tx.provider_amount} from coach {booking.coach.email} wallet balance. New balance: {wallet.balance}")
        logger.info(f"Refund process successfully completed for booking ID: {booking.id}")
        return refund
