from rest_framework import serializers
from .models import ProjectCategory


class ProjectCategorySerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source="repository.name", read_only=True)
    repository_owner = serializers.SerializerMethodField()
    repository_username = serializers.CharField(
        source="repository.user.username", read_only=True
    )
    repository_display_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectCategory
        fields = [
            "id",
            "repository",
            "repository_name",
            "repository_owner",
            "repository_username",
            "repository_display_name",
            "category",
            "confidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_repository_owner(self, obj):
        """Get the repository owner's display name or username"""
        user = obj.repository.user
        # Check if user has display_name field
        if hasattr(user, "display_name") and user.display_name:
            return user.display_name
        # Check if user has github_username field and it's not a numeric ID
        if hasattr(user, "github_username") and user.github_username:
            # Skip if it looks like a numeric ID (github_123456789)
            if not user.github_username.startswith("github_"):
                return user.github_username
        # Fallback to username
        return user.username

    def get_repository_display_name(self, obj):
        """Get the best display name for the repository owner"""
        user = obj.repository.user
        if hasattr(user, "display_name") and user.display_name:
            return user.display_name
        if hasattr(user, "github_username") and user.github_username:
            if not user.github_username.startswith("github_"):
                return user.github_username
        return user.username


class ProjectCategoryCreateSerializer(serializers.Serializer):
    repository_id = serializers.IntegerField(required=True)
    category = serializers.ChoiceField(choices=ProjectCategory.CategoryChoices.choices)
    confidence = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100
    )


class ProjectCategoryBulkCreateSerializer(serializers.Serializer):
    categories = ProjectCategoryCreateSerializer(many=True)


class ProjectCategoryStatsSerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()
    avg_confidence = serializers.FloatField()
    min_confidence = serializers.FloatField()
    max_confidence = serializers.FloatField()
