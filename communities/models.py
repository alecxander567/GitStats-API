from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone

class Community(models.Model):
    """
    Developer communities model
    """
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    cover_image = models.TextField(blank=True, null=True, help_text="URL to cover image")
    icon = models.TextField(blank=True, null=True, help_text="URL to icon image")
    language = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="Primary programming language for this community"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_communities'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communities'
        ordering = ['-created_at']
        verbose_name = 'Community'
        verbose_name_plural = 'Communities'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CommunityMember(models.Model):
    """
    Many-to-many relationship between users and communities with roles
    """
    
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MODERATOR = 'moderator', 'Moderator'
        MEMBER = 'member', 'Member'
    
    id = models.BigAutoField(primary_key=True)
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'community_members'
        unique_together = ['community', 'user']  # Prevent duplicate memberships
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['community', 'role']),
            models.Index(fields=['user']),
        ]
        verbose_name = 'Community Member'
        verbose_name_plural = 'Community Members'
    
    def __str__(self):
        return f"{self.user.username} - {self.community.name} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # If this is the first member of the community, make them an owner
        if not self.pk and not CommunityMember.objects.filter(community=self.community).exists():
            self.role = self.Role.OWNER
        super().save(*args, **kwargs)