from rest_framework import serializers
from .models import ReadmeProfile, ReadmeTemplate


class ReadmeProfileSerializer(serializers.ModelSerializer):
    """Serializer for README profiles"""

    username = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = ReadmeProfile
        fields = [
            "id",
            "user",
            "username",
            "display_name",
            "content",
            "template",
            "settings",
            "auto_update_enabled",
            "update_frequency",
            "last_generated",
            "next_update",
            "created_at",
            "updated_at",
            "export_count",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "user",
            "username",
            "display_name",
            "last_generated",
            "next_update",
            "created_at",
            "updated_at",
            "export_count",
        ]


class ReadmeTemplateSerializer(serializers.ModelSerializer):
    """Serializer for README templates"""

    class Meta:
        model = ReadmeTemplate
        fields = ["id", "name", "display_name", "description", "thumbnail", "is_active"]
