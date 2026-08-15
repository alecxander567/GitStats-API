from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "email",
            "avatar_url",
            "bio",
            "location",
            "company",
            "blog",
            "followers",
            "following",
            "public_repos",
            "github_created_at",
            "last_synced_at",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class UserSearchSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for user search - only returns essential fields
    """
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "email",
            "avatar_url",
        ]