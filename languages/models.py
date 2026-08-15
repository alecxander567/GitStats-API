from django.db import models
from repositories.models import Repository


class RepositoryLanguage(models.Model):
    """
    Model to track programming languages used in a repository
    """

    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="languages",
        db_column="repository_id",
    )
    language = models.CharField(max_length=100)
    bytes = models.BigIntegerField(help_text="Bytes of code written in this language")
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of the repository written in this language",
    )

    class Meta:
        db_table = "repository_languages"
        ordering = ["-percentage"]
        unique_together = [
            ["repository", "language"]
        ]  # Ensure unique language per repo

    def __str__(self):
        return f"{self.repository.name} - {self.language} ({self.percentage}%)"

    def save(self, *args, **kwargs):
        """
        Override save to ensure percentage is between 0 and 100
        """
        if self.percentage < 0:
            self.percentage = 0
        elif self.percentage > 100:
            self.percentage = 100
        super().save(*args, **kwargs)
