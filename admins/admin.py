from django.contrib import admin
from .models import CustomUser, Page

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'role', 'date_joined', 'is_staff')
    search_fields = ('email', 'name')
    list_filter = ('role', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'photo')}),
        ('Permissions', {'fields': ('role', 'assigned_pages', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined', 'last_login')
    ordering = ('email',)

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    
# python manage.py createsuperuser --email superadmin@cseku.ac.bd --name "Super Admin"    # 