from django.contrib import admin
from .models import Category

# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'image')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
