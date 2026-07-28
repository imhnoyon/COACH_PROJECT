from django.urls import include, path
from .views import CategoryCreateView   
urlpatterns = [
    path('categories/', CategoryCreateView.as_view(), name='category-create'),
]