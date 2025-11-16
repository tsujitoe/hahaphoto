from django.contrib import admin
from .models import Photo, PhotoCategory, PhotoTag


@admin.register(PhotoCategory)
class PhotoCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PhotoTag)
class PhotoTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'privacy', 'view_count', 'is_featured', 'created_at')
    list_filter = ('privacy', 'is_featured', 'created_at', 'category')
    search_fields = ('title', 'description', 'owner__username', 'tags__name')
    readonly_fields = ('created_at', 'updated_at', 'view_count', 'width', 'height', 'file_size')
    filter_horizontal = ('tags',)
    
    fieldsets = (
        ('Photo Information', {
            'fields': ('owner', 'title', 'description', 'image', 'thumbnail')
        }),
        ('Organization', {
            'fields': ('category', 'tags')
        }),
        ('Privacy & Status', {
            'fields': ('privacy', 'is_featured', 'view_count')
        }),
        ('Image Metadata', {
            'fields': ('width', 'height', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make owner readonly when editing existing photo"""
        readonly_fields = list(self.readonly_fields)
        if obj:  # Editing an existing object
            readonly_fields.append('owner')
        return readonly_fields
