from django.db import models
from django.conf import settings
from django.utils import timezone


class VisibilityChoices(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"


class Repository(models.Model):
    # Basic info
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="repositories"
    )
    github_repo_id = models.BigIntegerField(unique=True)

    # Repository details
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    visibility = models.CharField(
        max_length=10,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PUBLIC,
    )
    primary_language = models.CharField(max_length=100, blank=True, null=True)
    default_branch = models.CharField(max_length=100, default="main")

    # Stats
    stars = models.IntegerField(default=0)
    forks = models.IntegerField(default=0)
    watchers = models.IntegerField(default=0)
    open_issues = models.IntegerField(default=0)
    size = models.IntegerField(default=0)

    # Additional info
    license = models.CharField(max_length=100, blank=True, null=True)
    homepage = models.URLField(blank=True, null=True)
    archived = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)

    # GitHub timestamps
    created_at_github = models.DateTimeField()
    updated_at_github = models.DateTimeField()
    pushed_at = models.DateTimeField()

    # Local timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "repositories"
        ordering = ["-created_at_github"]
        indexes = [
            models.Index(fields=["user", "github_repo_id"]),
            models.Index(fields=["user", "-stars"]),
            models.Index(fields=["visibility"]),
            models.Index(fields=["primary_language"]),
            models.Index(fields=["archived"]),
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Ensure full_name is set if not provided
        if not self.full_name and self.user and self.name:
            self.full_name = f"{self.user.username}/{self.name}"
        super().save(*args, **kwargs)
