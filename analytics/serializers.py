from rest_framework import serializers
from .models import (
    RepositoryStats,
    UserStats,
    UpdateLog,
    Contributor,
    ContributorLanguages,
    ContributorActivity,
)
from repositories.models import Repository


class RepositoryStatsSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source="repository.name", read_only=True)
    repository_full_name = serializers.CharField(
        source="repository.full_name", read_only=True
    )
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = RepositoryStats
        fields = [
            "id",
            "repository",
            "repository_name",
            "repository_full_name",
            "user",
            "username",
            "stars",
            "forks",
            "watchers",
            "open_issues",
            "subscribers",
            "network",
            "size",
            "default_branch",
            "description",
            "language",
            "collected_at",
            "updated_at",
        ]
        read_only_fields = ["collected_at", "updated_at"]


class UserStatsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserStats
        fields = [
            "id",
            "user",
            "username",
            "email",
            "total_repos",
            "total_stars",
            "total_forks",
            "total_watchers",
            "total_open_issues",
            "public_repos",
            "private_repos",
            "followers",
            "following",
            "contributions",
            "collected_at",
            "updated_at",
        ]
        read_only_fields = ["collected_at", "updated_at"]


class UpdateLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    repository_name = serializers.CharField(
        source="repository.name", read_only=True, allow_null=True
    )

    class Meta:
        model = UpdateLog
        fields = [
            "id",
            "user",
            "username",
            "repository",
            "repository_name",
            "update_type",
            "status",
            "repositories_updated",
            "error_message",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "user",
            "started_at",
            "completed_at",
            "repositories_updated",
        ]


class ContributorLanguagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributorLanguages
        fields = ["id", "language", "bytes", "percentage"]


class ContributorSerializer(serializers.ModelSerializer):
    languages = ContributorLanguagesSerializer(many=True, read_only=True)
    repository_name = serializers.CharField(source="repository.name", read_only=True)
    repository_full_name = serializers.CharField(
        source="repository.full_name", read_only=True
    )

    class Meta:
        model = Contributor
        fields = [
            "id",
            "github_id",
            "login",
            "avatar_url",
            "html_url",
            "contributions",
            "recent_commits",
            "first_contribution_at",
            "last_contribution_at",
            "repository",
            "repository_name",
            "repository_full_name",
            "languages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ContributorBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating contributors"""

    repository_id = serializers.IntegerField()
    contributors = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )

    def validate_repository_id(self, value):
        try:
            Repository.objects.get(id=value)
            return value
        except Repository.DoesNotExist:
            raise serializers.ValidationError("Repository not found")


class RepositoryStatsCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating repository stats"""

    repository_id = serializers.IntegerField()
    stats = serializers.DictField()

    def validate(self, data):
        try:
            repository = Repository.objects.get(id=data["repository_id"])
        except Repository.DoesNotExist:
            raise serializers.ValidationError("Repository not found")
        return data


class BulkStatsSerializer(serializers.Serializer):
    """Serializer for bulk stats update"""

    repositories = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )

    def validate_repositories(self, value):
        if not value:
            raise serializers.ValidationError("At least one repository is required")
        return value


class StatsSummarySerializer(serializers.Serializer):
    """Serializer for summary statistics"""

    total_repositories = serializers.IntegerField()
    total_stars = serializers.IntegerField()
    total_forks = serializers.IntegerField()
    most_starred_repo = serializers.DictField(required=False)
    most_forked_repo = serializers.DictField(required=False)
    language_distribution = serializers.DictField()
    last_updated = serializers.DateTimeField(allow_null=True)


# ======================
# CONTRIBUTOR ACTIVITY SERIALIZERS
# ======================


class ContributorActivitySerializer(serializers.ModelSerializer):
    """Serializer for ContributorActivity model with additional computed fields."""

    repository_contributor_id = serializers.PrimaryKeyRelatedField(
        source="repository_contributor",
        queryset=Contributor.objects.all(),
        write_only=True,
    )
    total_contributions = serializers.IntegerField(read_only=True)
    net_changes = serializers.IntegerField(read_only=True)
    activity_score = serializers.FloatField(read_only=True)

    # Optional: Include nested contributor details
    contributor_name = serializers.SerializerMethodField()
    repository_name = serializers.SerializerMethodField()
    contributor_login = serializers.SerializerMethodField()

    class Meta:
        model = ContributorActivity
        fields = [
            "id",
            "repository_contributor_id",
            "contributor_login",
            "contributor_name",
            "repository_name",
            "period_start",
            "period_end",
            "commits",
            "pull_requests",
            "reviews",
            "issues",
            "additions",
            "deletions",
            "total_contributions",
            "net_changes",
            "activity_score",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_contributor_name(self, obj):
        """Get the contributor's full name or username."""
        if obj.repository_contributor and obj.repository_contributor.user:
            return obj.repository_contributor.user.get_full_name()
        return None

    def get_contributor_login(self, obj):
        """Get the contributor's login."""
        return obj.repository_contributor.login if obj.repository_contributor else None

    def get_repository_name(self, obj):
        """Get the repository name."""
        return (
            obj.repository_contributor.repository.name
            if obj.repository_contributor
            else None
        )

    def validate(self, data):
        """
        Validate that period_start is before period_end.
        """
        if data.get("period_start") and data.get("period_end"):
            if data["period_start"] >= data["period_end"]:
                raise serializers.ValidationError(
                    "period_start must be before period_end"
                )
        return data


class ContributorActivityListSerializer(serializers.Serializer):
    """Serializer for list endpoints with aggregation."""

    repository_contributor_id = serializers.IntegerField()
    contributor_login = serializers.CharField()
    contributor_name = serializers.CharField(required=False, allow_null=True)
    repository_name = serializers.CharField()
    total_commits = serializers.IntegerField()
    total_pull_requests = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    total_issues = serializers.IntegerField()
    total_additions = serializers.IntegerField()  # Changed from BigIntegerField
    total_deletions = serializers.IntegerField()  # Changed from BigIntegerField
    avg_activity_score = serializers.FloatField()
    period_count = serializers.IntegerField()


class ContributorActivityBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating contributor activities."""

    activities = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_activities(self, value):
        if not value:
            raise serializers.ValidationError("At least one activity is required")
        return value
