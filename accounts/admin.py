from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'is_email_verified', 'created_at')
    list_filter = ('is_email_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'bio', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('bio', 'avatar', 'location', 'birth_date', 'website')
        }),
        ('Account Status', {
            'fields': ('is_email_verified', 'created_at', 'updated_at')
        }),
    )
