
from django import views
from django.urls import include, path
from .views import *

urlpatterns = [
    path('register/', RegistrationAPIView.as_view(), name='register'),
]