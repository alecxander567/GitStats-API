from rest_framework import serializers
from .models import Repository, VisibilityChoices


class RepositorySerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    visibility_display = serializers.CharField(
        source="get_visibility_display", read_only=True
    )

    class Meta:
        model = Repository
        fields = [
            "id",
            "user",
            "github_repo_id",
            "name",
            "full_name",
            "description",
            "visibility",
            "visibility_display",
            "primary_language",
            "default_branch",
            "stars",
            "forks",
            "watchers",
            "open_issues",
            "size",
            "license",
            "homepage",
            "archived",
            "disabled",
            "created_at_github",
            "updated_at_github",
            "pushed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class RepositoryCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = [
            "github_repo_id",
            "name",
            "full_name",
            "description",
            "visibility",
            "primary_language",
            "default_branch",
            "stars",
            "forks",
            "watchers",
            "open_issues",
            "size",
            "license",
            "homepage",
            "archived",
            "disabled",
            "created_at_github",
            "updated_at_github",
            "pushed_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["user"] = request.user
        return super().create(validated_data)


class RepositoryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""

    class Meta:
        model = Repository
        fields = [
            "id",
            "name",
            "full_name",
            "description",
            "visibility",
            "primary_language",
            "stars",
            "forks",
            "archived",
            "updated_at_github",
        ]


class RepositoryStatsSerializer(serializers.Serializer):
    """Serializer for repository statistics"""

    total_repos = serializers.IntegerField()
    public_repos = serializers.IntegerField()
    private_repos = serializers.IntegerField()
    archived_repos = serializers.IntegerField()
    total_stars = serializers.IntegerField()
    total_forks = serializers.IntegerField()
    languages = serializers.DictField()
