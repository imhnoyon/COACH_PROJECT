from decimal import Decimal
from unittest.mock import patch
import stripe
from django.urls import reverse
from django.db import transaction
from rest_framework import status
from rest_framework.test import APITestCase
from Authentication.models import User
from Administration.models import Category
from Provider.models import Service, CoachProfile
from Payments.models import ServiceBooking, PaymentTransaction, ProviderWallet, WalletTransaction
from Payments.stripe_refund import StripeRefundService


class BookingRejectionTests(APITestCase):

    def setUp(self):
        # Create users
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        self.provider_user = User.objects.create_user(
            email="provider@example.com",
            password="password123",
            full_name="Jane Coach",
            role="Provider"
        )
        self.other_provider = User.objects.create_user(
            email="other@example.com",
            password="password123",
            full_name="Other Coach",
            role="Provider"
        )

        # Create Category
        self.category = Category.objects.create(name="Fitness", is_active=True)

        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Fitness Coach",
            is_completed=True,
            status="approved"
        )

        # Create Service
        self.service = Service.objects.create(
            coach=self.provider_user,
            title="Weight Loss Plan",
            category=self.category,
            description="Losing weight fast",
            service_type="one_time",
            session_format="video",
            session_duration=60,
            price=Decimal("100.00"),
            currency="USD",
            status="published"
        )

        # Create Service Booking (pending, paid)
        self.booking = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date="2026-08-10",
            booking_time="11:00:00",
            amount=Decimal("100.00"),
            currency="USD",
            status="pending",
            payment_status="paid"
        )

        # Create PaymentTransaction (10% fee, 90% provider earnings)
        self.payment_tx = PaymentTransaction.objects.create(
            customer=self.customer,
            coach=self.provider_user,
            booking=self.booking,
            stripe_payment_intent_id="pi_test_rejection123",
            gross_amount=Decimal("100.00"),
            platform_fee=Decimal("10.00"),
            provider_amount=Decimal("90.00"),
            currency="USD",
            status="succeeded"
        )

        # Set up provider wallet
        self.wallet = ProviderWallet.objects.create(user=self.provider_user, balance=Decimal("150.00"))

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.Charge.retrieve')
    @patch('stripe.Refund.create')
    def test_reject_booking_success(self, mock_refund_create, mock_charge_retrieve, mock_pi_retrieve):
        # Mock Stripe API return values
        mock_pi_retrieve.return_value.latest_charge = "ch_test_rejection123"
        mock_charge_retrieve.return_value.transfer = "tr_test_rejection123"
        mock_charge_retrieve.return_value.application_fee = "fee_test_rejection123"
        mock_refund_create.return_value.id = "re_test_rejection123"

        self.client.force_authenticate(user=self.provider_user)
        url = reverse('booking-reject', kwargs={'booking_id': self.booking.id})
        
        response = self.client.post(url, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify DB updates
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "rejected")
        self.assertEqual(self.booking.payment_status, "refunded")
        self.assertEqual(self.booking.refund_status, "completed")
        self.assertEqual(self.booking.refund_id, "re_test_rejection123")
        self.assertIsNotNone(self.booking.refunded_at)

        self.payment_tx.refresh_from_db()
        self.assertEqual(self.payment_tx.status, "refunded")
        self.assertEqual(self.payment_tx.stripe_charge_id, "ch_test_rejection123")
        self.assertEqual(self.payment_tx.stripe_transfer_id, "tr_test_rejection123")
        self.assertEqual(self.payment_tx.stripe_application_fee_id, "fee_test_rejection123")

        # Verify wallet balance was decremented by 90 (150 -> 60)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("60.00"))

        # Verify wallet debit transaction is logged
        wallet_tx = WalletTransaction.objects.filter(booking=self.booking, transaction_type="debit").first()
        self.assertIsNotNone(wallet_tx)
        self.assertEqual(wallet_tx.amount, Decimal("90.00"))
        self.assertEqual(wallet_tx.balance_after, Decimal("60.00"))

    def test_reject_booking_unauthorized(self):
        # Authenticate as a different coach
        self.client.force_authenticate(user=self.other_provider)
        url = reverse('booking-reject', kwargs={'booking_id': self.booking.id})
        
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])

        # Ensure no status change
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "pending")

    def test_reject_booking_not_paid(self):
        # Set payment_status to pending
        self.booking.payment_status = "pending"
        self.booking.save()

        self.client.force_authenticate(user=self.provider_user)
        url = reverse('booking-reject', kwargs={'booking_id': self.booking.id})
        
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_reject_booking_already_refunded(self):
        # Set payment_status to refunded
        self.booking.payment_status = "refunded"
        self.booking.refund_status = "completed"
        self.booking.refund_id = "re_123"
        self.booking.save()

        self.client.force_authenticate(user=self.provider_user)
        url = reverse('booking-reject', kwargs={'booking_id': self.booking.id})
        
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.Refund.create')
    def test_reject_booking_stripe_failure_rolls_back(self, mock_refund_create, mock_pi_retrieve):
        # Mock stripe to throw a CardError
        mock_pi_retrieve.return_value.latest_charge = "ch_test_rejection123"
        mock_refund_create.side_effect = stripe.error.CardError("Card declined", "param", "code")

        self.client.force_authenticate(user=self.provider_user)
        url = reverse('booking-reject', kwargs={'booking_id': self.booking.id})
        
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

        # Verify DB changes rolled back completely
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "pending")
        self.assertEqual(self.booking.payment_status, "paid")
        self.assertIsNone(self.booking.refund_id)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("150.00"))
