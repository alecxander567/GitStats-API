from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class ProjectCategory(models.Model):
    class CategoryChoices(models.TextChoices):
        WEB = "Web", "Web"
        MOBILE = "Mobile", "Mobile"
        DESKTOP = "Desktop", "Desktop"
        AI = "AI", "AI"
        API = "API", "API"
        CLI = "CLI", "CLI"
        IOT = "IoT", "IoT"
        GAME = "Game", "Game"
        LIBRARY = "Library", "Library"
        OTHER = "Other", "Other"

    repository = models.ForeignKey(
        "repositories.Repository",
        on_delete=models.CASCADE,
        related_name="project_categories",
    )
    category = models.CharField(
        max_length=20, choices=CategoryChoices.choices, db_index=True
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text="Confidence score from 0.00 to 100.00",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_categories"
        ordering = ["-confidence"]
        indexes = [
            models.Index(fields=["repository", "category"]),
            models.Index(fields=["category", "confidence"]),
        ]
        unique_together = [
            ["repository", "category"]
        ]  # One category per repository per category type

    def __str__(self):
        return f"{self.repository.name} - {self.category} ({self.confidence}%)"
