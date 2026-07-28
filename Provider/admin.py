from django.contrib import admin
from .models import CoachProfile, Certification, Qualification


@admin.register(CoachProfile)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'about', 'user', 'get_categories', 'expertises', 'created_at', 'updated_at')
    search_fields = ('about',)
    list_filter = ('created_at', 'updated_at')
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
