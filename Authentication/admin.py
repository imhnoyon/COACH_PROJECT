from django.contrib import admin
from .models import User



@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email','phone_number', 'is_staff', 'is_active', 'is_superuser', 'role','latitude','longitude', 'created_at', 'updated_at')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('full_name', 'email')
    ordering = ('id',)