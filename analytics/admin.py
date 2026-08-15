from django.contrib import admin
from .models import (
    RepositoryStats,
    UserStats,
    UpdateLog,
    Contributor,
    ContributorLanguages,
)


@admin.register(RepositoryStats)
class RepositoryStatsAdmin(admin.ModelAdmin):
    list_display = ["repository", "user", "stars", "forks", "collected_at"]
    list_filter = ["user", "collected_at", "language"]
    search_fields = ["repository__name", "repository__full_name", "user__username"]
    readonly_fields = ["collected_at", "updated_at"]
    ordering = ["-collected_at"]


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ["user", "total_repos", "total_stars", "total_forks", "collected_at"]
    list_filter = ["user", "collected_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["collected_at", "updated_at"]
    ordering = ["-collected_at"]


@admin.register(UpdateLog)
class UpdateLogAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "update_type",
        "status",
        "repositories_updated",
        "started_at",
    ]
    list_filter = ["user", "update_type", "status", "started_at"]
    search_fields = ["user__username", "repository__name"]
    readonly_fields = ["started_at"]
    ordering = ["-started_at"]


class ContributorLanguagesInline(admin.TabularInline):
    model = ContributorLanguages
    extra = 1
    fields = ["language", "bytes", "percentage"]


@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ["login", "repository", "contributions", "created_at"]
    list_filter = ["repository", "user"]
    search_fields = ["login", "repository__name", "github_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ContributorLanguagesInline]
    ordering = ["-contributions"]


@admin.register(ContributorLanguages)
class ContributorLanguagesAdmin(admin.ModelAdmin):
    list_display = ["contributor", "language", "bytes", "percentage"]
    list_filter = ["language"]
    search_fields = ["contributor__login", "language"]
    ordering = ["-bytes"]
