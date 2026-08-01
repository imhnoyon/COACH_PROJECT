from django.urls import path
from .views import (
    ServiceBookingCreateView,
    ServiceBookingDetailView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    ProductPurchaseView,
    ProductOrdersListView
)

urlpatterns = [
    path('book-service/', ServiceBookingCreateView.as_view(), name='book-service'),
    path('orders/', ServiceBookingCreateView.as_view(), name='order-list'),
    path('orders/<int:booking_id>/', ServiceBookingDetailView.as_view(), name='order-detail'),
    
    # Stripe Checkout and Webhook
    path('stripe/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='stripe-create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    
    # Products Purchases
    path('products/purchase/', ProductPurchaseView.as_view(), name='product-purchase'),
    path('products/orders/', ProductOrdersListView.as_view(), name='product-orders-list'),
]

