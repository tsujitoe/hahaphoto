from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from PIL import Image
import os
from io import BytesIO
from django.core.files.base import ContentFile


class PhotoCategory(models.Model):
    """Category for organizing photos"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')  # For emoji or icon name
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Photo Category')
        verbose_name_plural = _('Photo Categories')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class PhotoTag(models.Model):
    """Tag for tagging photos"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Photo Tag')
        verbose_name_plural = _('Photo Tags')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Photo(models.Model):
    """Model for storing user-uploaded photos"""
    
    PRIVACY_CHOICES = [
        ('public', _('Public')),
        ('private', _('Private')),
        ('friends', _('Friends Only')),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(
        upload_to='photos/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/%d/',
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        PhotoCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='photos'
    )
    tags = models.ManyToManyField(PhotoTag, blank=True, related_name='photos')
    
    # Metadata
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Image metadata
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes

    class Meta:
        verbose_name = _('Photo')
        verbose_name_plural = _('Photos')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['privacy', '-created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save to generate thumbnail and optimize images"""
        # Store file size
        if self.image:
            self.file_size = self.image.size
        
        super().save(*args, **kwargs)
        
        # Generate thumbnail and optimize image (only if not using cloud storage or if local path available)
        if self.image:
            try:
                self._generate_thumbnail()
                self._optimize_image()
                self._extract_image_info()
            except (OSError, AttributeError) as e:
                # GCS and other cloud storage backends don't support .path or save to local filesystem
                # Fall back to just extracting metadata from the file
                try:
                    self._extract_image_info_from_file()
                except Exception as extract_err:
                    print(f"Warning: Could not extract image info: {extract_err}")

    def _generate_thumbnail(self):
        """Generate a thumbnail from the original image"""
        try:
            img = Image.open(self.image.path)
            img.thumbnail((300, 300))
            
            # Create thumbnail filename
            thumb_path = self.image.path.replace('photos', 'thumbnails')
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            
            # Save thumbnail
            img.save(thumb_path, quality=85, optimize=True)
            
            # Update thumbnail field
            self.thumbnail.name = self.image.name.replace('photos', 'thumbnails')
        except Exception as e:
            print(f"Error generating thumbnail: {e}")

    def _optimize_image(self):
        """Optimize the original image"""
        try:
            img = Image.open(self.image.path)
            
            # Resize if too large
            max_width = 2000
            max_height = 2000
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                img.save(self.image.path, quality=90, optimize=True)
        except Exception as e:
            print(f"Error optimizing image: {e}")

    def _extract_image_info(self):
        """Extract width and height from image (local file)"""
        try:
            img = Image.open(self.image.path)
            self.width = img.width
            self.height = img.height
            super().save(update_fields=['width', 'height'])
        except Exception as e:
            print(f"Error extracting image info: {e}")

    def _extract_image_info_from_file(self):
        """Extract width and height from image (file-like object, works with cloud storage)"""
        try:
            # Read from the file object directly (works with GCS, S3, etc.)
            img = Image.open(self.image.file)
            self.width = img.width
            self.height = img.height
            super().save(update_fields=['width', 'height'])
        except Exception as e:
            print(f"Error extracting image info from file object: {e}")

    def increment_view_count(self):
        """Increment the view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    @property
    def aspect_ratio(self):
        """Calculate aspect ratio for responsive image display"""
        if self.width and self.height:
            return (self.width / self.height) * 100
        return None
