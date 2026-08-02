import os
from decimal import Decimal
import stripe
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from utils.api_response import APIResponse
from Provider.models import Product



from .models import (
    ServiceBooking,
    ProviderWallet,
    WalletTransaction,
    PaymentTransaction,
    StripeWebhookLog
)
from .serializers import (
    ServiceBookingCreateSerializer,
    ServiceBookingDetailSerializer,
    ProductPurchaseCreateSerializer
)

# Initialize Stripe API Key
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.environ.get('STRIPE_SECRET_KEY')


class ServiceBookingCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        """Order/Book a service with date, time, and session details."""
        serializer = ServiceBookingCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        booking = serializer.save()
        res_serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Service order created successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def get(self, request):
        """Retrieve list of service orders / bookings for the authenticated user or coach."""
        if getattr(request.user, 'role', None) == 'Provider':
            bookings = ServiceBooking.objects.filter(coach=request.user)\
                .select_related('user', 'coach', 'service', 'service__category')
        else:
            bookings = ServiceBooking.objects.filter(user=request.user)\
                .select_related('user', 'coach', 'service', 'service__category')

        serializer = ServiceBookingDetailSerializer(bookings, many=True, context={'request': request})
        return APIResponse.success(
            message="Service orders retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class ServiceBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, booking_id, user):
        try:
            return ServiceBooking.objects.select_related('user', 'coach', 'service', 'service__category').get(
                id=booking_id
            )
        except ServiceBooking.DoesNotExist:
            return None

    def get(self, request, booking_id):
        """Retrieve details of a specific service order / booking."""
        booking = self.get_object(booking_id, request.user)
        if not booking:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if booking.user != request.user and booking.coach != request.user:
            return APIResponse.error(
                message="You do not have permission to view this booking.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def patch(self, request, booking_id):
        """Update status or payment status of a booking."""
        booking = self.get_object(booking_id, request.user)
        if not booking:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if booking.user != request.user and booking.coach != request.user:
            return APIResponse.error(
                message="You do not have permission to modify this booking.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        allowed_fields = ['status', 'payment_status', 'payment_method', 'transaction_id', 'notes']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        for attr, val in update_data.items():
            setattr(booking, attr, val)
        booking.save()

        res_serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a Stripe Checkout Session for a ServiceBooking (service or product)."""
        booking_id = request.data.get('booking_id')
        product_id = request.data.get('product_id')

        if not booking_id and not product_id:
            return APIResponse.error("Either booking_id or product_id must be provided.", status_code=status.HTTP_400_BAD_REQUEST)
        if booking_id and product_id:
            return APIResponse.error("Provide only booking_id or product_id, not both.", status_code=status.HTTP_400_BAD_REQUEST)

        success_url = request.data.get('success_url', 'http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}')
        cancel_url = request.data.get('cancel_url', 'http://localhost:3000/payment/cancel')

        try:
            if booking_id:
                booking = get_object_or_404(ServiceBooking, id=booking_id, user=request.user)
                if booking.payment_status == 'paid':
                    return APIResponse.error("This order has already been paid.", status_code=status.HTTP_400_BAD_REQUEST)
                
                amount_cents = int(booking.amount * 100)
                if booking.service:
                    name = f"Booking for {booking.service.title}"
                elif booking.product:
                    name = f"Purchase of {booking.product.title}"
                else:
                    name = "Marketplace Order"
            else:
                product = get_object_or_404(Product, id=product_id)
                # Create a ServiceBooking representing this product purchase in pending state
                booking = ServiceBooking.objects.create(
                    user=request.user,
                    coach=product.coach,
                    product=product,
                    amount=product.price,
                    currency='USD',
                    payment_status='pending',
                    status='pending'
                )
                amount_cents = int(booking.amount * 100)
                name = f"Purchase of {product.title}"

            metadata = {
                'type': 'booking',
                'id': str(booking.id),
                'customer_id': str(request.user.id)
            }

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=request.user.email,
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': name,
                            },
                            'unit_amount': amount_cents,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata
            )

            return APIResponse.success(
                message="Checkout session created successfully.",
                data={
                    'session_id': checkout_session.id,
                    'checkout_url': checkout_session.url
                }
            )

        except Exception as e:
            return APIResponse.error(f"Stripe error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Handle Stripe webhook events."""
        try:
            payload = request.body
            sig_header = request.headers.get('STRIPE_SIGNATURE')
            webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None) or os.environ.get('STRIPE_WEBHOOK_SECRET')

            if not sig_header or not webhook_secret:
                return APIResponse.error("Stripe signature or webhook secret missing.", status_code=status.HTTP_400_BAD_REQUEST)

            try:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            except ValueError:
                return APIResponse.error("Invalid payload.", status_code=status.HTTP_400_BAD_REQUEST)
            except stripe.error.SignatureVerificationError:
                return APIResponse.error("Invalid signature.", status_code=status.HTTP_400_BAD_REQUEST)

            event_id = event.id if hasattr(event, 'id') else event.get('id')
            event_type = event.type if hasattr(event, 'type') else event.get('type')

            # Convert to dictionary safely for dict-like nested lookup compatibility
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else event

            # Idempotency check
            if StripeWebhookLog.objects.filter(event_id=event_id).exists():
                return APIResponse.success(message="Event already processed.")

            # Log the event
            StripeWebhookLog.objects.create(event_id=event_id, event_type=event_type)

            if event_type == 'checkout.session.completed':
                session = event_dict.get('data', {}).get('object', {})
                payment_intent_id = session.get('payment_intent')
                metadata = session.get('metadata', {})
                
                ref_type = metadata.get('type')
                ref_id = metadata.get('id')

                if not ref_type or not ref_id:
                    return APIResponse.error("Missing metadata in session.", status_code=status.HTTP_400_BAD_REQUEST)

                gross_amount = Decimal(session.get('amount_total', 0)) / 100
                currency = session.get('currency', 'usd').upper()

                with transaction.atomic():
                    if ref_type == 'booking':
                        booking = get_object_or_404(ServiceBooking, id=ref_id)
                        if booking.payment_status == 'paid':
                            return APIResponse.success(message="Order already paid.")

                        
                        booking.payment_status = 'paid'
                        booking.transaction_id = payment_intent_id
                        booking.payment_method = 'stripe'

                        # Set status based on booking type for services only
                        if booking.service:
                            if booking.service.booking_type == 'instant':
                                booking.status = 'confirmed'
                            elif booking.service.booking_type == 'approval':
                                booking.status = 'pending'

                        booking.save()

                        coach = booking.coach
                        customer = booking.user
                        booking_obj = booking
                    else:
                        return APIResponse.error("Unknown metadata type.", status_code=status.HTTP_400_BAD_REQUEST)

                    # Calculate marketplace split (10% platform commission, 90% provider earnings)
                    platform_fee = gross_amount * Decimal('0.10')
                    provider_earnings = gross_amount - platform_fee

                    # Record global PaymentTransaction
                    PaymentTransaction.objects.create(
                        customer=customer,
                        coach=coach,
                        booking=booking_obj,
                        stripe_payment_intent_id=payment_intent_id or f"direct_{event_id}",
                        gross_amount=gross_amount,
                        platform_fee=platform_fee,
                        provider_amount=provider_earnings,
                        currency=currency,
                        status='succeeded'
                    )

                    # Deposit to Provider Wallet
                    wallet, _ = ProviderWallet.objects.get_or_create(user=coach)
                    wallet.balance = Decimal(str(wallet.balance)) + provider_earnings
                    wallet.save()

                    # Record Wallet Transaction log
                    if booking_obj.product_id:
                        desc = f"Earnings from product purchase #{booking_obj.id}"
                    else:
                        desc = f"Earnings from booking #{booking_obj.id}"

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='credit',
                        amount=provider_earnings,
                        balance_after=wallet.balance,
                        description=desc,
                        booking=booking_obj
                    )

            return APIResponse.success(message="Webhook handled successfully.")
        except Exception as e:
            import traceback
            err_trace = traceback.format_exc()
            with open("webhook_error.txt", "w") as f:
                f.write(err_trace)
            return APIResponse.error(
                message=f"Webhook exception: {str(e)}",
                errors={"traceback": err_trace},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a pending product purchase in ServiceBooking table."""
        serializer = ProductPurchaseCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return APIResponse.error(message="Validation error", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        order = serializer.save()
        res_serializer = ServiceBookingDetailSerializer(order, context={'request': request})
        return APIResponse.success(
            message="Product purchase order created successfully. Proceed to payment.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class ProductOrdersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all product purchase orders for the user from ServiceBooking."""
        if getattr(request.user, 'role', None) == 'Provider':
            orders = ServiceBooking.objects.filter(product__coach=request.user)\
                .select_related('user', 'product', 'coach')
        else:
            orders = ServiceBooking.objects.filter(user=request.user, product__isnull=False)\
                .select_related('user', 'product', 'coach')

        serializer = ServiceBookingDetailSerializer(orders, many=True, context={'request': request})
        return APIResponse.success(
            message="Product purchase orders retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

