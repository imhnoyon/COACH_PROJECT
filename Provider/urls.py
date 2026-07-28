from django.urls import path
from .views import *

urlpatterns = [
    path('categories-list/', CategoryListView.as_view(), name='category-list'),
    path('coach-profile/', CoachProfileView.as_view(), name='coach-profile'),
    path('services/create/', ServiceCreateView.as_view(), name='service-create'),
    path('services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
    path('retrive-services/<int:service_id>/', ServiceCreateView.as_view(), name='service-detail'),
]