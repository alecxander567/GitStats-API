from django.contrib import admin
from .models import ReadmeProfile, ReadmeGenerationHistory, ReadmeTemplate


@admin.register(ReadmeProfile)
class ReadmeProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "template",
        "auto_update_enabled",
        "last_generated",
        "next_update",
        "export_count",
    ]
    list_filter = ["template", "auto_update_enabled", "is_active"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["last_generated", "next_update", "created_at", "updated_at"]

    fieldsets = (
        ("User Information", {"fields": ("user", "is_active")}),
        ("Content", {"fields": ("content", "template")}),
        ("Settings", {"fields": ("settings",)}),
        (
            "Auto-Update",
            {
                "fields": (
                    "auto_update_enabled",
                    "update_frequency",
                    "last_generated",
                    "next_update",
                )
            },
        ),
        ("Metadata", {"fields": ("export_count", "created_at", "updated_at")}),
    )


@admin.register(ReadmeGenerationHistory)
class ReadmeGenerationHistoryAdmin(admin.ModelAdmin):
    list_display = ["profile", "generated_at", "status", "content_length"]
    list_filter = ["status"]
    search_fields = ["profile__user__username"]
    readonly_fields = ["generated_at"]


@admin.register(ReadmeTemplate)
class ReadmeTemplateAdmin(admin.ModelAdmin):
    list_display = ["display_name", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "display_name"]
