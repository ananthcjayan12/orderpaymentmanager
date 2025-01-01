from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Company, Agent

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'user_type', 'is_active', 'date_joined', 'last_login')
    list_filter = ('user_type', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
    )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subscription_status', 'created_at')
    list_filter = ('subscription_status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'gstin')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'phone', 'email', 'website', 'gstin', 'logo')
        }),
        ('Subscription Details', {
            'fields': ('subscription_status', 'subscription_end_date')
        }),
        ('Branding', {
            'fields': ('primary_color', 'secondary_color')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company', 'role', 'status', 'total_collections', 'collection_efficiency')
    list_filter = ('company', 'role', 'status', 'created_at')
    search_fields = ('full_name', 'user__email', 'company__name')
    readonly_fields = ('created_at', 'updated_at', 'last_active')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'company')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'address', 'id_proof_type', 'id_proof_number')
        }),
        ('Role & Status', {
            'fields': ('role', 'status')
        }),
        ('Performance Metrics', {
            'fields': ('total_collections', 'total_orders', 'collection_target')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_active'),
            'classes': ('collapse',)
        }),
    )
    
    def collection_efficiency(self, obj):
        return f"{obj.collection_efficiency:.1f}%"
    collection_efficiency.short_description = 'Collection Efficiency'
