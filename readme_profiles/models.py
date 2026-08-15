from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


class ReadmeProfile(models.Model):
    """Store user's README profile configuration and content"""

    TEMPLATE_CHOICES = [
        ("modern", "Modern"),
        ("minimal", "Minimal"),
        ("dark", "Dark Theme"),
        ("visual", "Visual Heavy"),
        ("professional", "Professional"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="readme_profile",
    )

    # Content
    content = models.TextField(
        default="",
        help_text="Markdown content with placeholders like {{user.name}}, {{stats.total_stars}}, etc.",
    )
    generated_content = models.TextField(
        default="",
        blank=True,
        help_text="Last fully-resolved output (placeholders filled in, badges/chart "
        "injected). This is what gets displayed/exported - `content` above stays "
        "as the raw editable template and is never overwritten by generation.",
    )
    template = models.CharField(
        max_length=50, choices=TEMPLATE_CHOICES, default="modern"
    )

    # Settings (which stats to include)
    settings = models.JSONField(default=dict, blank=True)
    # Example settings:
    # {
    #   "show_stats": True,
    #   "show_languages": True,
    #   "show_contributions": True,
    #   "show_activity_chart": True,
    #   "show_badges": True,
    #   "theme": "dark",
    #   "accent_color": "#6C63FF"
    # }

    # Auto-update settings
    auto_update_enabled = models.BooleanField(default=True)
    update_frequency = models.CharField(
        max_length=20,
        choices=[("weekly", "Weekly"), ("daily", "Daily"), ("monthly", "Monthly")],
        default="weekly",
    )

    # Timestamps
    last_generated = models.DateTimeField(null=True, blank=True)
    next_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    export_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "readme_profiles"
        verbose_name = "README Profile"
        verbose_name_plural = "README Profiles"

    def __str__(self):
        return f"{self.user.username}'s README Profile"

    def save(self, *args, **kwargs):
        if not self.next_update and self.auto_update_enabled:
            self.schedule_next_update()
        super().save(*args, **kwargs)

    def schedule_next_update(self):
        """Schedule the next update based on frequency"""
        if self.update_frequency == "daily":
            delta = timezone.timedelta(days=1)
        elif self.update_frequency == "weekly":
            delta = timezone.timedelta(days=7)
        elif self.update_frequency == "monthly":
            delta = timezone.timedelta(days=30)
        else:
            delta = timezone.timedelta(days=7)

        self.next_update = timezone.now() + delta

    @property
    def is_update_due(self):
        """Check if the profile needs to be updated"""
        if not self.next_update:
            return True
        return timezone.now() >= self.next_update


class ReadmeGenerationHistory(models.Model):
    """Track when READMEs were generated"""

    profile = models.ForeignKey(
        ReadmeProfile, on_delete=models.CASCADE, related_name="generation_history"
    )

    generated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("success", "Success"),
            ("failed", "Failed"),
            ("in_progress", "In Progress"),
        ],
        default="in_progress",
    )
    error_message = models.TextField(blank=True, null=True)
    content_length = models.IntegerField(default=0)

    class Meta:
        db_table = "readme_generation_history"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"


class ReadmeTemplate(models.Model):
    """Pre-defined templates with placeholders"""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    thumbnail = models.TextField(blank=True, null=True)
    markdown_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "readme_templates"
        ordering = ["name"]

    def __str__(self):
        return self.display_name
