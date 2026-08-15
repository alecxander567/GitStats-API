from django.contrib import admin
from .models import ProjectCategory


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "repository", "category", "confidence", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["repository__name", "category"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-confidence"]

    fieldsets = (
        (None, {"fields": ("repository", "category", "confidence")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
