from django.urls import include, path
from .views import *

urlpatterns = [
    path('create-user-post/', PostCreateView.as_view(), name='create-post'),
    path('coach-profile-list/',CoachProfileView.as_view(),name='coach-profile'),
    path('recommended-coach-profile-list/',RecommendedCoachProfileView.as_view(),name='recommended-coach-profile'),
    path('user-category-list/', CategoryListView.as_view(), name='category-list'),
    path('coach-profile-review/<int:coach_id>/', CoachRatingAPIView.as_view(), name='coach-profile-review'),
    path('app-rating/', AppRatingAPIView.as_view(), name='app-rating'),
    path('app-ratings-list/', AppRatingListView.as_view(), name='app-ratings-list'),
    path('coach-profile/<int:coach_id>/', CoachProfileDetailView.as_view(), name='coach-profile-detail'),
    path('blog-list/', BlogListView.as_view(), name='blog-list'),
    path('blog-detail/<int:blog_id>/', BlogDetailView.as_view(), name='blog-detail'),
    
]