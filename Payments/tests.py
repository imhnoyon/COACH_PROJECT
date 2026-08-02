from decimal import Decimal
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from Authentication.models import User
from Administration.models import Category
from Provider.models import Service, Product, CoachProfile
from Payments.models import (
    ServiceBooking,
    ProviderWallet,
    WalletTransaction,
    PaymentTransaction,
    StripeWebhookLog
)


class PaymentsTests(APITestCase):

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

        # Create Product
        self.product = Product.objects.create(
            coach=self.provider_user,
            category=self.category,
            title="E-Book: Nutrition Guide",
            description="Eat clean guide",
            price=Decimal("50.00"),
            status="published"
        )

        # Create Service Booking
        self.booking = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date="2026-08-10",
            booking_time="11:00:00",
            amount=Decimal("100.00"),
            currency="USD",
            status="pending",
            payment_status="pending"
        )

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_for_booking(self, mock_stripe_create):
        # Mock stripe response
        mock_stripe_create.return_value.id = "cs_test_booking123"
        mock_stripe_create.return_value.url = "https://checkout.stripe.com/pay/cs_test_booking123"

        self.client.force_authenticate(user=self.customer)
        url = reverse('stripe-create-checkout-session')
        data = {'booking_id': self.booking.id}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['session_id'], "cs_test_booking123")
        self.assertEqual(response.data['data']['checkout_url'], "https://checkout.stripe.com/pay/cs_test_booking123")

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_for_product(self, mock_stripe_create):
        mock_stripe_create.return_value.id = "cs_test_product123"
        mock_stripe_create.return_value.url = "https://checkout.stripe.com/pay/cs_test_product123"

        self.client.force_authenticate(user=self.customer)
        url = reverse('stripe-create-checkout-session')
        data = {'product_id': self.product.id}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify ServiceBooking represents this product purchase (dates null, product linked)
        self.assertTrue(ServiceBooking.objects.filter(
            user=self.customer,
            product=self.product,
            service__isnull=True,
            booking_date__isnull=True,
            booking_time__isnull=True
        ).exists())

    @patch('stripe.Webhook.construct_event')
    def test_webhook_payment_paid_split_logic(self, mock_construct_event):
        # Mock webhook event construct
        mock_construct_event.return_value = {
            'id': 'evt_booking_paid_123',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'payment_intent': 'pi_test_booking123',
                    'amount_total': 10000,  # $100.00
                    'currency': 'usd',
                    'metadata': {
                        'type': 'booking',
                        'id': str(self.booking.id),
                        'customer_id': str(self.customer.id)
                    }
                }
            }
        }

        url = reverse('stripe-webhook')
        headers = {'HTTP_STRIPE_SIGNATURE': 'valid_sig'}
        
        response = self.client.post(url, data=b"{}", content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify booking updated to paid
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'paid')
        self.assertEqual(self.booking.transaction_id, 'pi_test_booking123')

        # Verify PaymentTransaction created with 10% / 90% split
        tx = PaymentTransaction.objects.get(stripe_payment_intent_id='pi_test_booking123')
        self.assertEqual(tx.gross_amount, Decimal("100.00"))
        self.assertEqual(tx.platform_fee, Decimal("10.00"))  # 10% commission
        self.assertEqual(tx.provider_amount, Decimal("90.00"))  # 90% provider earnings
        self.assertEqual(tx.booking, self.booking)

        # Verify ProviderWallet holds the provider's earnings
        wallet = ProviderWallet.objects.get(user=self.provider_user)
        self.assertEqual(wallet.balance, Decimal("90.00"))

        # Verify WalletTransaction was logged
        wallet_tx = WalletTransaction.objects.get(wallet=wallet, booking=self.booking)
        self.assertEqual(wallet_tx.transaction_type, 'credit')
        self.assertEqual(wallet_tx.amount, Decimal("90.00"))
        self.assertEqual(wallet_tx.balance_after, Decimal("90.00"))

    @patch('stripe.Webhook.construct_event')
    def test_webhook_idempotency(self, mock_construct_event):
        StripeWebhookLog.objects.create(event_id="evt_processed_123", event_type="checkout.session.completed")

        mock_construct_event.return_value = {
            'id': 'evt_processed_123',
            'type': 'checkout.session.completed'
        }

        url = reverse('stripe-webhook')
        headers = {'HTTP_STRIPE_SIGNATURE': 'valid_sig'}
        
        # Call webhook with duplicate event
        response = self.client.post(url, data=b"{}", content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Event already processed.")

    def test_overlapping_booking_validation(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('book-service')
        
        # Try to book the same date and same time slot (overlapping with self.booking)
        data = {
            'service_id': self.service.id,
            'booking_date': '2026-08-10',
            'booking_time': '11:00 AM'
        }
        
        response = self.client.post(url, data, format='json')
        # Should fail with validation error (400 Bad Request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

        # Try to book a different time slot on the same date
        different_time_data = {
            'service_id': self.service.id,
            'booking_date': '2026-08-10',
            'booking_time': '02:00 PM'
        }
        
        response = self.client.post(url, different_time_data, format='json')
        # Should succeed (201 Created)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

