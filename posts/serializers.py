from rest_framework import serializers
from .models import Post
from django.contrib.auth import get_user_model
from communities.models import Community

User = get_user_model()


class PostSerializer(serializers.ModelSerializer):
    """
    Post serializer for list and detail views
    """

    community_name = serializers.CharField(source="community.name", read_only=True)
    community_slug = serializers.CharField(source="community.slug", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    user_display_name = serializers.CharField(
        source="user.display_name", read_only=True
    )
    user_avatar_url = serializers.CharField(source="user.avatar_url", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "community",
            "community_name",
            "community_slug",
            "user",
            "user_id",
            "username",
            "user_display_name",
            "user_avatar_url",
            "title",
            "content",
            "github_repo_url",
            "blog_url",
            "created_at",
            "updated_at",
            "is_owner",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for create and update operations
    """

    community_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Post
        fields = [
            "id",
            "community",
            "community_id",
            "user",
            "title",
            "content",
            "github_repo_url",
            "blog_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user", "community"]

    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Post title must be at least 3 characters long."
            )
        return value.strip()

    def validate_content(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Post content must be at least 10 characters long."
            )
        return value.strip()

    def validate(self, data):
        # If community_id is provided, validate and set community
        if "community_id" in data:
            try:
                community = Community.objects.get(id=data["community_id"])
                data["community"] = community
            except Community.DoesNotExist:
                raise serializers.ValidationError(
                    {"community_id": "Community does not exist."}
                )
            # Remove community_id from validated data as it's not a model field
            del data["community_id"]

        # If community is provided via URL, it will be set in the view
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["user"] = request.user
        return super().create(validated_data)
