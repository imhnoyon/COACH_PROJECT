from django.urls import path
from .views import (
    ServiceBookingCreateView,
    ServiceBookingDetailView,
    CreatePaymentView,
    CapturePaymentView,
    CompleteServiceBookingView,
    RefundPaymentView,
    ProviderWalletView,
    WithdrawalRequestView,
    WithdrawalHistoryView,
    AdminWithdrawalListView,
    AdminApproveWithdrawalView,
    AdminRejectWithdrawalView,
    PayPalWebhookView,
)

urlpatterns = [
    # Booking routes
    path('book-service/', ServiceBookingCreateView.as_view(), name='book-service'),
    path('orders/', ServiceBookingCreateView.as_view(), name='order-list'),
    path('orders/<int:booking_id>/', ServiceBookingDetailView.as_view(), name='order-detail'),
    path('orders/<int:booking_id>/complete/', CompleteServiceBookingView.as_view(), name='order-complete'),

    # Payment routes
    path('create/', CreatePaymentView.as_view(), name='payment-create'),
    path('capture/', CapturePaymentView.as_view(), name='payment-capture'),
    path('refund/', RefundPaymentView.as_view(), name='payment-refund'),

    # Provider Wallet & Withdrawal routes
    path('wallet/', ProviderWalletView.as_view(), name='provider-wallet'),
    path('withdraw/request/', WithdrawalRequestView.as_view(), name='withdraw-request'),
    path('withdraw/history/', WithdrawalHistoryView.as_view(), name='withdraw-history'),

    # Admin Withdrawal routes
    path('admin/withdraw/', AdminWithdrawalListView.as_view(), name='admin-withdraw-list'),
    path('admin/withdraw/<int:id>/approve/', AdminApproveWithdrawalView.as_view(), name='admin-withdraw-approve'),
    path('admin/withdraw/<int:id>/reject/', AdminRejectWithdrawalView.as_view(), name='admin-withdraw-reject'),

    # PayPal Webhook
    path('webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),
]
