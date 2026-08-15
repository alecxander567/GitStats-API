from django.contrib import admin
from .models import RepositoryLanguage


@admin.register(RepositoryLanguage)
class RepositoryLanguageAdmin(admin.ModelAdmin):
    list_display = ["repository", "language", "bytes", "percentage"]
    list_filter = ["language", "repository"]
    search_fields = ["language", "repository__name"]
    ordering = ["repository", "-percentage"]
    readonly_fields = ["id"]
