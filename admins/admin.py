# admins/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import CustomUser, Page, Blog, Role, CommitteeMembership, SystemSetting,Alumni

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'name',
        'current_role_display',        
        'date_joined',
        'is_staff',
        'is_active',
    )
    search_fields = ('email', 'name')
    list_filter = (
        'is_staff',
        'is_active',
        'date_joined',
        
    )
    readonly_fields = ('date_joined', 'last_login')
    ordering = ('email',)

    def current_role_display(self, obj):
        """Show the current year's role (or 'None')"""
        membership = obj.current_membership
        if membership and membership.role:
            role_name = membership.role.name
            if membership.role.is_president:
                return format_html('<strong style="color: #0066cc;">{} (President)</strong>', role_name)
            return role_name
        return "—"
    
    current_role_display.short_description = "Current Role"

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'photo', 'student_id', 'phone_number')}),
        ('Status', {'fields': ('is_active', 'is_staff')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )



@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'approval_status', 'category', 'author',
        'date', 'restricted', 'created_by', 'created_at'
    )
    list_filter = ('approval_status', 'category', 'restricted', 'date')
    search_fields = ('title', 'excerpt', 'author')
    date_hierarchy = 'date'


# Optionally register new models
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_president', 'created_by', 'created_at')
    list_filter = ('is_president',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)


@admin.register(CommitteeMembership)
class CommitteeMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'year', 'assigned_at')
    list_filter = ('year', 'role__is_president')
    search_fields = ('user__email', 'user__name', 'role__name')
    date_hierarchy = 'assigned_at'

@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'batch',
        'session',
        'passing_year',          # ← comment out
        'current_role',
        'company',
        'location',
        'approval_status',
        'created_at',
        'phone_number',          # ← comment out
        'about',                 # ← comment out
        'linkedin_url',          # ← comment out
        'facebook_url',          # ← comment out
        'approved_by',
    )
    list_filter = ('approval_status', 'batch', 'created_at')
    search_fields = ('name', 'email', 'batch', 'current_role', 'company')
    readonly_fields = ('created_at', 'updated_at', 'approved_by')
    list_per_page = 20
    ordering = ('-created_at',)

    # Optional: add this to avoid future surprises
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('approved_by')

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')