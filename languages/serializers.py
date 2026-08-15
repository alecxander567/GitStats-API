from rest_framework import serializers
from .models import RepositoryLanguage


class RepositoryLanguageSerializer(serializers.ModelSerializer):
    """
    Serializer for RepositoryLanguage model
    """

    repository_name = serializers.CharField(source="repository.name", read_only=True)
    repository_owner = serializers.CharField(
        source="repository.owner.username", read_only=True
    )

    class Meta:
        model = RepositoryLanguage
        fields = [
            "id",
            "repository",
            "repository_name",
            "repository_owner",
            "language",
            "bytes",
            "percentage",
        ]
        read_only_fields = ["id", "repository_name", "repository_owner"]


class RepositoryLanguageSummarySerializer(serializers.Serializer):
    """
    Serializer for language summary across all repositories
    """

    language = serializers.CharField()
    total_bytes = serializers.IntegerField()
    total_repositories = serializers.IntegerField()
    average_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class RepositoryLanguageCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk create/update operations
    """

    languages = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )

    def validate_languages(self, value):
        """
        Validate that each language entry has required fields
        """
        required_fields = ["language", "bytes", "percentage"]
        for lang in value:
            for field in required_fields:
                if field not in lang:
                    raise serializers.ValidationError(
                        f"Missing required field: {field}"
                    )

            # Validate percentage range
            if not 0 <= float(lang["percentage"]) <= 100:
                raise serializers.ValidationError(
                    f"Percentage must be between 0 and 100. Got: {lang['percentage']}"
                )
        return value
