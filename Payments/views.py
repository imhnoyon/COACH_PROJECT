from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from utils.api_response import APIResponse

from .models import (
    ServiceBooking,
    Payment,
    ProviderWallet,
    WithdrawalRequest,
    Refund
)
from .serializers import (
    ServiceBookingCreateSerializer,
    ServiceBookingDetailSerializer,
    PaymentSerializer,
    ProviderWalletSerializer,
    WithdrawalRequestSerializer,
    RefundSerializer,
    CreatePaymentInputSerializer,
    CapturePaymentInputSerializer,
    RefundInputSerializer,
    WithdrawalRequestInputSerializer,
    RejectWithdrawalInputSerializer
)
from .payment_service import PaymentService
from .permissions import IsAdminUser, IsProviderUser


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

        if booking.user != request.user and booking.coach != request.user and getattr(request.user, 'role', None) != 'Admin':
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

        if booking.user != request.user and booking.coach != request.user and getattr(request.user, 'role', None) != 'Admin':
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


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """POST /payments/create/ - Create a PayPal payment order for a booking."""
        serializer = CreatePaymentInputSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment, paypal_response = PaymentService.create_payment_order(
                booking_id=serializer.validated_data['booking_id'],
                customer=request.user,
                return_url=serializer.validated_data.get('return_url'),
                cancel_url=serializer.validated_data.get('cancel_url')
            )
            res_serializer = PaymentSerializer(payment, context={'request': request})
            links = paypal_response.get('links', [])
            approval_url = next((link['href'] for link in links if link.get('rel') == 'approve'), None)

            return APIResponse.success(
                message="PayPal order created successfully.",
                data={
                    "payment": res_serializer.data,
                    "approval_url": approval_url,
                    "paypal_order": paypal_response
                },
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=f"PayPal order creation failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CapturePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """POST /payments/capture/ - Capture funds for a PayPal order."""
        serializer = CapturePaymentInputSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = PaymentService.capture_payment_order(
                paypal_order_id=serializer.validated_data['paypal_order_id'],
                user=request.user
            )
            res_serializer = PaymentSerializer(payment, context={'request': request})
            return APIResponse.success(
                message="PayPal payment captured successfully. Provider earnings held in pending balance.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=f"PayPal capture failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompleteServiceBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        """POST /orders/<booking_id>/complete/ - Complete service and shift pending balance to available balance."""
        try:
            booking = PaymentService.complete_service(booking_id=booking_id, user=request.user)
            res_serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
            return APIResponse.success(
                message="Service marked as completed. Earnings are now in provider's available balance.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RefundPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        """POST /payments/refund/ - Process a full PayPal refund for a payment."""
        serializer = RefundInputSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            refund = PaymentService.process_payment_refund(
                payment_id=serializer.validated_data['payment_id'],
                refunded_by=request.user,
                reason=serializer.validated_data.get('reason')
            )
            res_serializer = RefundSerializer(refund, context={'request': request})
            return APIResponse.success(
                message="PayPal payment refunded successfully.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=f"Refund failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProviderWalletView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]

    def get(self, request):
        """GET /wallet/ - Retrieve provider's wallet balance details."""
        wallet, _ = ProviderWallet.objects.get_or_create(provider=request.user)
        serializer = ProviderWalletSerializer(wallet, context={'request': request})
        return APIResponse.success(
            message="Provider wallet retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class WithdrawalRequestView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]

    def post(self, request):
        """POST /withdraw/request/ - Submit a new withdrawal request."""
        serializer = WithdrawalRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            withdrawal = PaymentService.submit_withdrawal_request(
                provider=request.user,
                amount=serializer.validated_data['amount'],
                paypal_email=serializer.validated_data['paypal_email']
            )
            res_serializer = WithdrawalRequestSerializer(withdrawal, context={'request': request})
            return APIResponse.success(
                message="Withdrawal request submitted successfully.",
                data=res_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WithdrawalHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]

    def get(self, request):
        """GET /withdraw/history/ - List withdrawal requests history for authenticated provider."""
        withdrawals = WithdrawalRequest.objects.filter(provider=request.user)
        serializer = WithdrawalRequestSerializer(withdrawals, many=True, context={'request': request})
        return APIResponse.success(
            message="Withdrawal history retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class AdminWithdrawalListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        """GET /admin/withdraw/ - Admin views all withdrawal requests."""
        withdrawals = WithdrawalRequest.objects.all().select_related('provider', 'approved_by')
        serializer = WithdrawalRequestSerializer(withdrawals, many=True, context={'request': request})
        return APIResponse.success(
            message="All withdrawal requests retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class AdminApproveWithdrawalView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, id):
        """POST /admin/withdraw/{id}/approve/ - Admin approves withdrawal request and sends payout via PayPal."""
        try:
            withdrawal = PaymentService.approve_withdrawal_request(withdrawal_id=id, admin_user=request.user)
            res_serializer = WithdrawalRequestSerializer(withdrawal, context={'request': request})
            return APIResponse.success(
                message="Withdrawal approved and PayPal payout processed successfully.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=f"PayPal payout failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminRejectWithdrawalView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, id):
        """POST /admin/withdraw/{id}/reject/ - Admin rejects withdrawal request."""
        serializer = RejectWithdrawalInputSerializer(data=request.data)

        reason = None
        if serializer.is_valid():
            reason = serializer.validated_data.get('reason')

        try:
            withdrawal = PaymentService.reject_withdrawal_request(withdrawal_id=id, admin_user=request.user, reason=reason)
            res_serializer = WithdrawalRequestSerializer(withdrawal, context={'request': request})
            return APIResponse.success(
                message="Withdrawal request rejected successfully.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValueError as ve:
            return APIResponse.error(message=str(ve), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PayPalWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """POST /webhook/ - Handles PayPal Webhook notifications."""
        success, msg = PaymentService.handle_webhook_event(
            headers=request.headers,
            raw_body=request.body
        )

        if not success:
            return APIResponse.error(message=msg, status_code=status.HTTP_400_BAD_REQUEST)

        return APIResponse.success(message="Webhook processed successfully.", data={"status": msg}, status_code=status.HTTP_200_OK)
