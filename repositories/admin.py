from django.contrib import admin
from .models import Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "full_name",
        "user",
        "visibility",
        "stars",
        "forks",
        "archived",
    ]
    list_filter = ["visibility", "archived", "disabled", "primary_language"]
    search_fields = ["name", "full_name", "description"]
    readonly_fields = ["github_repo_id", "created_at", "updated_at"]
    ordering = ["-stars"]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "user",
                    "github_repo_id",
                    "name",
                    "full_name",
                    "description",
                    "visibility",
                )
            },
        ),
        (
            "GitHub Details",
            {"fields": ("primary_language", "default_branch", "license", "homepage")},
        ),
        (
            "Statistics",
            {"fields": ("stars", "forks", "watchers", "open_issues", "size")},
        ),
        ("Status", {"fields": ("archived", "disabled")}),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at_github",
                    "updated_at_github",
                    "pushed_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
