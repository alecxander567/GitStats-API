from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # Remove unused AbstractUser fields by setting them to None
    first_name = None
    last_name = None
    is_staff = None
    is_superuser = None
    groups = None
    user_permissions = None

    # Only keep what we need
    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    blog = models.CharField(max_length=255, null=True, blank=True)
    followers = models.IntegerField(default=0)
    following = models.IntegerField(default=0)
    public_repos = models.IntegerField(default=0)
    github_created_at = models.DateTimeField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    github_token = models.TextField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    class Meta:
        db_table = "users_user"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
            models.Index(fields=["github_id"]),
        ]
