from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone


class Post(models.Model):
    """
    Community posts model for sharing content, repositories, and blog links
    """

    id = models.BigAutoField(primary_key=True)
    community = models.ForeignKey(
        "communities.Community", on_delete=models.CASCADE, related_name="posts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    github_repo_url = models.TextField(null=True, blank=True)
    blog_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        indexes = [
            models.Index(fields=["community", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.community.name}"
