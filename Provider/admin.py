from django.contrib import admin
from .models import *


@admin.register(CoachProfile)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'is_completed', 'get_categories','status', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name', 'about')
    list_filter = ('status', 'is_completed', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = 'Categories'


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'coach', 'name', 'document', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'coach', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'coach', 'service_type', 'session_format', 'booking_type', 'status', 'created_at', 'updated_at')
    search_fields = ('title',)
    list_filter = ('service_type', 'session_format', 'booking_type', 'status', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    
@admin.register(ClientBenefit)
class ClientBenefitAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'outcome')
    search_fields = ('outcome',)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'coach', 'created_at', 'updated_at')
    search_fields = ('title',)
    list_filter = ('category', 'coach', 'created_at', 'updated_at')
    ordering = ('-created_at',)