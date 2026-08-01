from django.urls import path
from .views import *

urlpatterns = [
    path('categories-list/', CategoryListView.as_view(), name='category-list'),
    path('coach-profile/', CoachProfileView.as_view(), name='coach-profile'),
    path('services/create/', ServiceCreateView.as_view(), name='service-create'),
    path('services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
    path('retrive-services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
    path('blogs/create/', BlogCreateView.as_view(), name='blog-create'),
    path('blogs/<int:blog_id>/', BlogCreateView.as_view(), name='blog-detail'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products-list/', productListView.as_view(), name='product-list'),
    path('products/<int:product_id>/', ProductCreateView.as_view(), name='product-detail'),

]