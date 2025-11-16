from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from PIL import Image


class UserProfile(models.Model):
    """Extend Django User model with additional profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True, default='')
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    location = models.CharField(max_length=100, blank=True, default='')
    birth_date = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_email_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        """Override save to optimize avatar image"""
        super().save(*args, **kwargs)
        
        # Optimize avatar image if it exists
        if self.avatar:
            img = Image.open(self.avatar.path)
            
            # Resize image if too large
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.avatar.path)


# Signal to create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Automatically save the UserProfile when the User is saved"""
    instance.profile.save()
