from django.urls import path
from .views import CategoryListView, CoachProfileView

urlpatterns = [
    path('categories-list/', CategoryListView.as_view(), name='category-list'),
    path('coach-profile/', CoachProfileView.as_view(), name='coach-profile'),
]