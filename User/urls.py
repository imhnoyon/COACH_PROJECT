from django.urls import include, path
from .views import CategoryListView, CoachProfileView, PostCreateView

urlpatterns = [
    path('create-user-post/', PostCreateView.as_view(), name='create-post'),
    path('coach-profile-list/',CoachProfileView.as_view(),name='coach-profile'),
    path('user-category-list/', CategoryListView.as_view(), name='category-list'),
]