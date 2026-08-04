from django.contrib import admin
from .models import *

@admin.register(Post)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at')
    search_fields = ('title', 'user__username')
    list_filter = ('created_at',)


@admin.register(CoachRating)
class CoachRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'coach', 'user', 'rating','review', 'created_at')
    # search_fields = ('coach__user__username', 'user__username')
    list_filter = ('rating', 'created_at')
    
    
@admin.register(AppRating)
class AppRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rating','review', 'created_at')
    list_filter = ('rating', 'created_at')