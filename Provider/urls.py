from django.urls import path
from .views import *

urlpatterns = [
    path('categories-list/', CategoryListView.as_view(), name='category-list'),
    path('coach-profile/', CoachProfileView.as_view(), name='coach-profile'),
    path('provider-list-profile/', CoachProfileListView.as_view(), name='provider-profile'),
    path('provider-list-profile/<int:profile_id>/', CoachProfileListView.as_view(), name='provider-profile'),
    path('services/create/', ServiceCreateView.as_view(), name='service-create'),
    path('services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
    path('retrive-services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
    path('blogs/create/', BlogCreateView.as_view(), name='blog-create'),
    path('blogs/<int:blog_id>/', BlogCreateView.as_view(), name='blog-detail'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products-list/', productListView.as_view(), name='product-list'),
    path('products/<int:product_id>/', ProductCreateView.as_view(), name='product-detail'),
    
    #services list for provider
    path('services-list/', ServiceListView.as_view(), name='service-list'),
    path('user-products-list/', ProductsListView.as_view(), name='product-list'),
    path('services-bookings-list/', ServiceBookingPendingAPIView.as_view(), name='service-booking-list'),
    path('service-accept/<int:booking_id>/', markAsConfirmedAPIView.as_view(), name='service-booking-accept'),
    path('service-reject/<int:booking_id>/', markAsRejectedAPIView.as_view(), name='service-booking-reject'),
    

    # Payment related endpoints
    path('provider-wallet/', ProviderWalletView.as_view(), name='provider-wallet'),

]