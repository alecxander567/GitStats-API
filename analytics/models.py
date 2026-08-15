from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from repositories.models import Repository

User = get_user_model()


class RepositoryStats(models.Model):
    """Track statistics for repositories over time"""

    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="stats"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="repository_stats"
    )

    stars = models.IntegerField(default=0)
    forks = models.IntegerField(default=0)
    watchers = models.IntegerField(default=0)
    open_issues = models.IntegerField(default=0)
    subscribers = models.IntegerField(default=0)
    network = models.IntegerField(default=0)
    size = models.IntegerField(default=0)
    default_branch = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=100, blank=True, null=True)

    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["repository", "collected_at"]),
            models.Index(fields=["user", "collected_at"]),
        ]
        unique_together = ["repository", "collected_at"]

    def __str__(self):
        return (
            f"{self.repository.name} - {self.collected_at.strftime('%Y-%m-%d %H:%M')}"
        )


class UserStats(models.Model):
    """Track user statistics over time"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stats")

    total_repos = models.IntegerField(default=0)
    total_stars = models.IntegerField(default=0)
    total_forks = models.IntegerField(default=0)
    total_watchers = models.IntegerField(default=0)
    total_open_issues = models.IntegerField(default=0)
    public_repos = models.IntegerField(default=0)
    private_repos = models.IntegerField(default=0)
    followers = models.IntegerField(default=0)
    following = models.IntegerField(default=0)
    contributions = models.IntegerField(default=0)

    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["user", "collected_at"]),
        ]
        unique_together = ["user", "collected_at"]

    def __str__(self):
        return f"{self.user.username} - {self.collected_at.strftime('%Y-%m-%d %H:%M')}"


class UpdateLog(models.Model):
    """Track when updates were performed"""

    UPDATE_TYPES = [
        ("MANUAL", "Manual"),
        ("SCHEDULED", "Scheduled"),
        ("WEBHOOK", "Webhook"),
        ("INITIAL", "Initial"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="update_logs")
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="update_logs",
    )

    update_type = models.CharField(
        max_length=20, choices=UPDATE_TYPES, default="MANUAL"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("IN_PROGRESS", "In Progress"),
            ("SUCCESS", "Success"),
            ("FAILED", "Failed"),
        ],
        default="PENDING",
    )

    repositories_updated = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.update_type} - {self.status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"


class Contributor(models.Model):
    """Model to store GitHub contributors"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="contributors"
    )
    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="contributors"
    )

    # GitHub contributor info
    github_id = models.BigIntegerField()  # REMOVED unique=True
    login = models.CharField(max_length=255)
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    html_url = models.URLField(max_length=500, blank=True, null=True)

    # Contribution stats
    contributions = models.IntegerField(default=0)

    # Recent commits snapshot (list of {sha, message, date, url}), captured
    # during sync so the UI can show activity without live GitHub calls.
    recent_commits = models.JSONField(default=list, blank=True)

    # Timestamps
    first_contribution_at = models.DateTimeField(null=True, blank=True)
    last_contribution_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-contributions"]
        unique_together = ["repository", "github_id"]  # Uniqueness per repository
        indexes = [
            models.Index(fields=["repository", "contributions"]),
            models.Index(fields=["user", "login"]),
        ]

    def __str__(self):
        return f"{self.login} - {self.repository.name}"


class ContributorLanguages(models.Model):
    """Stores the languages associated with each contributor's work"""

    contributor = models.ForeignKey(
        Contributor, on_delete=models.CASCADE, related_name="languages"
    )
    language = models.CharField(max_length=100)
    bytes = models.BigIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        ordering = ["-bytes"]
        unique_together = ["contributor", "language"]
        indexes = [
            models.Index(fields=["contributor", "bytes"]),
            models.Index(fields=["language"]),
        ]

    def __str__(self):
        return f"{self.contributor.login} - {self.language} ({self.percentage}%)"


class ContributorActivity(models.Model):
    """
    Stores historical activity data for repository contributors.
    Used for calculating trends and activity levels.
    """

    repository_contributor = models.ForeignKey(
        Contributor,
        on_delete=models.CASCADE,
        related_name="activities",
        db_column="repository_contributor_id",
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    commits = models.IntegerField(default=0)
    pull_requests = models.IntegerField(default=0)
    reviews = models.IntegerField(default=0)
    issues = models.IntegerField(default=0)
    additions = models.BigIntegerField(default=0)
    deletions = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contributor_activity"
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["repository_contributor", "period_start"]),
            models.Index(fields=["period_start", "period_end"]),
        ]
        unique_together = [["repository_contributor", "period_start", "period_end"]]

    def __str__(self):
        return f"{self.repository_contributor} - {self.period_start.date()}"

    @property
    def total_contributions(self):
        """Calculate total contributions for the period."""
        return self.commits + self.pull_requests + self.reviews + self.issues

    @property
    def net_changes(self):
        """Calculate net code changes (additions - deletions)."""
        return self.additions - self.deletions

    @property
    def activity_score(self):
        """
        Calculate an activity score based on all metrics.
        Can be used for ranking contributors.
        """
        # Weight different activities
        score = (
            self.commits * 1.0
            + self.pull_requests * 2.0
            + self.reviews * 1.5
            + self.issues * 1.0
            + (self.additions + self.deletions) * 0.01  # Scale down large numbers
        )
        return round(score, 2)
