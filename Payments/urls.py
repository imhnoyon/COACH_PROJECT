from django.urls import path
from .views import ServiceBookingCreateView, ServiceBookingDetailView

urlpatterns = [
    path('book-service/', ServiceBookingCreateView.as_view(), name='book-service'),
    path('orders/', ServiceBookingCreateView.as_view(), name='order-list'),
    path('orders/<int:booking_id>/', ServiceBookingDetailView.as_view(), name='order-detail'),
]
